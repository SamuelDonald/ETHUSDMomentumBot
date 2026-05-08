import asyncio
import time

from eth_scalper_engine.bridge.zmq_sender import ZMQSignalSender
from eth_scalper_engine.config.settings import SETTINGS
from eth_scalper_engine.core.delta_engine import DeltaEngine
from eth_scalper_engine.core.orderbook_imbalance import OrderBookImbalanceEngine
from eth_scalper_engine.core.pressure_engine import PressureEngine
from eth_scalper_engine.data.bybit_ws import BybitWebSocketClient
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

    ws_client = BybitWebSocketClient(
        symbol=SETTINGS.bybit.symbol,
        depth_levels=SETTINGS.bybit.depth_levels,
    )

    delta_engine         = DeltaEngine(window=SETTINGS.strategy.delta_window)
    imbalance_engine     = OrderBookImbalanceEngine(window=SETTINGS.strategy.imbalance_window)
    pressure_engine      = PressureEngine(
        delta_engine=delta_engine,
        imbalance_engine=imbalance_engine,
        epsilon=SETTINGS.strategy.pressure_epsilon,
    )
    trend_filter         = EmaTrendFilter(
        period=SETTINGS.strategy.ema_period,
        slope_threshold=SETTINGS.strategy.ema_slope_threshold,
    )
    consolidation_filter = ConsolidationFilter(
        candles=SETTINGS.strategy.consolidation_candles,
        threshold_multiplier=SETTINGS.strategy.consolidation_threshold_multiplier,
    )
    bos_detector   = BOSDetector(lookback=SETTINGS.strategy.bos_lookback)
    signal_engine  = SignalEngine(
        rr=SETTINGS.strategy.risk_reward,
        signal_cooldown=SETTINGS.strategy.signal_cooldown,
        max_signal_age=SETTINGS.strategy.max_signal_age,
    )
    sender = ZMQSignalSender(
        endpoint=SETTINGS.bridge.zmq_endpoint,
        high_water_mark=SETTINGS.bridge.high_water_mark,
    )

    latest_orderbook    = OrderBookSnapshot()
    latest_trend        = "flat"
    latest_market_state = "tradable"
    latest_bos          = None
    latest_swing_high   = None
    latest_swing_low    = None
    latest_1m_candle_id = 0
    latest_bid_vol      = 0.0
    latest_ask_vol      = 0.0

    logger.info("Starting ETHUSD scalper engine (Bybit REST polling)")

    try:
        async for payload in ws_client.stream():
            topic, data = ws_client.get_stream_and_data(payload)
            if not topic or data is None:
                continue

            # ── TRADES ──────────────────────────────────────────────────────
            # Bybit REST recent-trade list (newest first):
            # each item: [time, side, size, price, tickDirection, id, isBlockTrade]
            # index:       0     1     2     3
            if topic.startswith("publicTrade."):
                trades = data if isinstance(data, list) else [data]
                last_price = None
                for trade in trades:
                    if isinstance(trade, list):
                        # REST format: [timestamp, side, size, price, ...]
                        side  = str(trade[1])   # "Buy" or "Sell"
                        qty   = float(trade[2])
                        price = float(trade[3])
                    else:
                        # WebSocket format (fallback)
                        side  = str(trade.get("S", "Buy"))
                        qty   = float(trade.get("v", 0))
                        price = float(trade.get("p", 0))

                    if price <= 0 or qty <= 0:
                        continue

                    # "Buy" = aggressor bought = taker buy = is_buyer_maker False
                    is_buyer_maker = (side == "Sell")
                    delta_engine.update_trade(
                        price=price, quantity=qty, is_buyer_maker=is_buyer_maker
                    )
                    last_price = price

                if last_price is None or not latest_orderbook.bids or not latest_orderbook.asks:
                    continue

                pressure_state    = pressure_engine.evaluate(
                    bid_volume=latest_bid_vol,
                    ask_volume=latest_ask_vol,
                )
                normalized_symbol = symbol_mapper.normalize_symbol(
                    SETTINGS.symbols.canonical_symbol
                )
                signal = signal_engine.generate(
                    symbol=SETTINGS.symbols.canonical_symbol,
                    normalized_symbol=normalized_symbol,
                    entry_price=last_price,
                    pressure=pressure_state.state,
                    trend=latest_trend,
                    bos=latest_bos,
                    market_state=latest_market_state,
                    swing_high=latest_swing_high,
                    swing_low=latest_swing_low,
                    signal_candle_id=latest_1m_candle_id,
                )

                logger.info(
                    "pressure=%s delta=%.2f bid=%.2f ask=%.2f trend=%s bos=%s market=%s price=%.2f",
                    pressure_state.state, pressure_state.delta,
                    pressure_state.bid_volume, pressure_state.ask_volume,
                    latest_trend, latest_bos, latest_market_state, last_price,
                )

                if signal:
                    sent = sender.send(signal)
                    logger.info("Signal %s sent=%s", signal.get("signal"), sent)

            # ── ORDER BOOK ───────────────────────────────────────────────────
            elif topic.startswith("orderbook."):
                msg_type         = payload.get("type", "snapshot")
                latest_orderbook = parse_depth_message(data, msg_type)
                latest_bid_vol, latest_ask_vol = imbalance_engine.update(latest_orderbook)

            # ── 5M KLINE ─────────────────────────────────────────────────────
            elif topic.startswith("kline.5."):
                candles = data if isinstance(data, list) else [data]
                for candle in candles:
                    if candle.get("confirm"):
                        kline = {
                            "o": candle["open"],
                            "c": candle["close"],
                            "h": candle["high"],
                            "l": candle["low"],
                            "v": candle["volume"],
                            "t": candle["start"],
                            "x": True,
                        }
                        result       = trend_filter.update(kline)
                        latest_trend = str(result["trend"])
                        logger.info("Trend: %s slope=%.5f", latest_trend, result["slope"])

            # ── 1M KLINE ─────────────────────────────────────────────────────
            elif topic.startswith("kline.1."):
                candles = data if isinstance(data, list) else [data]
                for candle in candles:
                    if candle.get("confirm"):
                        kline = {
                            "o": candle["open"],
                            "c": candle["close"],
                            "h": candle["high"],
                            "l": candle["low"],
                            "v": candle["volume"],
                            "t": candle["start"],
                            "x": True,
                        }
                        latest_market_state = consolidation_filter.update(kline)["state"]
                        bos_result          = bos_detector.update(kline)
                        latest_bos          = bos_result["bos"]
                        latest_swing_high   = bos_result["swing_high"]
                        latest_swing_low    = bos_result["swing_low"]
                        latest_1m_candle_id = int(candle["start"])
                        signal_engine.set_candle_id(latest_1m_candle_id)
                        logger.info(
                            "BOS: %s high=%s low=%s market=%s",
                            latest_bos, latest_swing_high,
                            latest_swing_low, latest_market_state,
                        )

    finally:
        sender.close()


if __name__ == "__main__":
    asyncio.run(run_engine())
