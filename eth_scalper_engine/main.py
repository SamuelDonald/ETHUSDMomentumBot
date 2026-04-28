import asyncio

from eth_scalper_engine.bridge.zmq_sender import ZMQSignalSender
from eth_scalper_engine.config.settings import SETTINGS
from eth_scalper_engine.core.delta_engine import DeltaEngine
from eth_scalper_engine.core.orderbook_imbalance import OrderBookImbalanceEngine
from eth_scalper_engine.core.pressure_engine import PressureEngine
from eth_scalper_engine.data.binance_ws import BinanceWebSocketClient
from eth_scalper_engine.data.orderbook import OrderBookSnapshot, parse_depth_message
from eth_scalper_engine.strategy.bos_detector import BOSDetector
from eth_scalper_engine.strategy.consolidation import ConsolidationFilter
from eth_scalper_engine.strategy.ema_trend import EmaTrendFilter
from eth_scalper_engine.strategy.signal_engine import SignalEngine
from eth_scalper_engine.utils.logger import setup_logger
from eth_scalper_engine.utils.symbol_mapper import SymbolMapper


async def run_engine() -> None:
    logger = setup_logger()

    symbol_mapper = SymbolMapper(
        canonical_symbol=SETTINGS.symbols.canonical_symbol,
        broker_symbol_map=SETTINGS.symbols.broker_symbol_map,
    )

    ws_client = BinanceWebSocketClient(
        ws_base_url=SETTINGS.binance.ws_base_url,
        symbol=SETTINGS.binance.symbol,
        depth_levels=SETTINGS.binance.depth_levels,
    )

    delta_engine = DeltaEngine(window=SETTINGS.strategy.delta_window)
    imbalance_engine = OrderBookImbalanceEngine(window=SETTINGS.strategy.imbalance_window)
    pressure_engine = PressureEngine(
        delta_engine=delta_engine,
        imbalance_engine=imbalance_engine,
        epsilon=SETTINGS.strategy.pressure_epsilon,
    )

    trend_filter = EmaTrendFilter(
        period=SETTINGS.strategy.ema_period,
        slope_threshold=SETTINGS.strategy.ema_slope_threshold,
    )
    consolidation_filter = ConsolidationFilter(
        candles=SETTINGS.strategy.consolidation_candles,
        threshold_multiplier=SETTINGS.strategy.consolidation_threshold_multiplier,
    )
    bos_detector = BOSDetector(lookback=SETTINGS.strategy.bos_lookback)
    signal_engine = SignalEngine(
        rr=SETTINGS.strategy.risk_reward,
        signal_cooldown=SETTINGS.strategy.signal_cooldown,
        max_signal_age=SETTINGS.strategy.max_signal_age,
    )
    sender = ZMQSignalSender(
        endpoint=SETTINGS.bridge.zmq_endpoint,
        high_water_mark=SETTINGS.bridge.high_water_mark,
    )

    latest_orderbook = OrderBookSnapshot()
    latest_trend = "flat"
    latest_market_state = "tradable"
    latest_bos = None
    latest_swing_high = None
    latest_swing_low = None
    latest_1m_close = None
    latest_1m_close_time = 0

    logger.info("Starting ETHUSD scalper engine")

    try:
        async for payload in ws_client.stream():
            stream_name, data = ws_client.get_stream_and_data(payload)
            if not stream_name or not data:
                continue

            if stream_name.endswith("@trade"):
                price = float(data["p"])
                qty = float(data["q"])
                is_buyer_maker = bool(data["m"])

                delta_engine.update_trade(price=price, quantity=qty, is_buyer_maker=is_buyer_maker)

                if not latest_orderbook.bids or not latest_orderbook.asks:
                    logger.warning("Order book data missing; skipping signal decision")
                    continue

                bid_vol, ask_vol = imbalance_engine.update(latest_orderbook)
                pressure_state = pressure_engine.evaluate(bid_volume=bid_vol, ask_volume=ask_vol)

                normalized_symbol = symbol_mapper.normalize_symbol(SETTINGS.symbols.canonical_symbol)
                signal = signal_engine.generate(
                    symbol=SETTINGS.symbols.canonical_symbol,
                    normalized_symbol=normalized_symbol,
                    entry_price=latest_1m_close if latest_1m_close is not None else price,
                    pressure=pressure_state.state,
                    trend=latest_trend,
                    bos=latest_bos,
                    market_state=latest_market_state,
                    swing_high=latest_swing_high,
                    swing_low=latest_swing_low,
                    signal_time=latest_1m_close_time,
                )

                logger.info(
                    "pressure=%s delta=%.2f mean=%.2f bid=%.2f ask=%.2f trend=%s bos=%s market=%s",
                    pressure_state.state,
                    pressure_state.delta,
                    pressure_state.delta_mean,
                    pressure_state.bid_volume,
                    pressure_state.ask_volume,
                    latest_trend,
                    latest_bos,
                    latest_market_state,
                )

                if signal:
                    sent = sender.send(signal)
                    if sent:
                        logger.info("Signal sent: %s", signal)
                    else:
                        logger.warning("Signal dropped (non-blocking send or invalid payload): %s", signal)
                else:
                    logger.info("Signal rejected by strategy gates or safety checks")

            elif "@depth" in stream_name:
                latest_orderbook = parse_depth_message(data)

            elif stream_name.endswith("@kline_5m"):
                kline = data.get("k", {})
                if kline.get("x"):
                    trend_result = trend_filter.update(kline)
                    latest_trend = str(trend_result["trend"])
                    logger.info("Trend update: %s (slope=%.5f)", latest_trend, trend_result["slope"])

            elif stream_name.endswith("@kline_1m"):
                kline = data.get("k", {})
                if kline.get("x"):
                    latest_market_state = consolidation_filter.update(kline)["state"]
                    bos_result = bos_detector.update(kline)
                    latest_bos = bos_result["bos"]
                    latest_swing_high = bos_result["swing_high"]
                    latest_swing_low = bos_result["swing_low"]
                    latest_1m_close = float(kline["c"])
                    latest_1m_close_time = int(float(kline.get("T", 0)) / 1000)
                    logger.info(
                        "BOS update: %s swing_high=%s swing_low=%s | Market state: %s",
                        latest_bos,
                        latest_swing_high,
                        latest_swing_low,
                        latest_market_state,
                    )

            await asyncio.sleep(SETTINGS.loop_sleep_seconds)
    finally:
        sender.close()


if __name__ == "__main__":
    asyncio.run(run_engine())
