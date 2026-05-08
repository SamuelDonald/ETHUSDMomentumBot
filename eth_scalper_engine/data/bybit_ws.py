"""
bybit_rest.py — Bybit REST API polling client
Replaces WebSocket entirely. Works through any network restriction.
Polls Bybit V5 REST endpoints every second for:
  - Recent trades (delta engine)
  - Order book (imbalance engine)
  - 1M klines (BOS + consolidation)
  - 5M klines (EMA trend)

Named bybit_ws.py intentionally so main.py import works unchanged.
"""
import asyncio
import time
import urllib.request
import json
from typing import Any, AsyncIterator, Dict, Optional, Tuple


BASE = "https://api.bybit.com"


def _get(path: str, params: dict) -> dict:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url   = f"{BASE}{path}?{query}"
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read())


class BybitWebSocketClient:
    """
    REST polling client with same interface as BybitWebSocketClient.
    main.py calls ws_client.stream() and ws_client.get_stream_and_data()
    — both work identically to the WebSocket version.
    """

    def __init__(self, ws_base_url: str = BASE,
                 symbol: str = "ETHUSDT",
                 depth_levels: int = 20):
        self.symbol       = symbol.upper()
        self.depth_levels = min(depth_levels, 50)   # Bybit max for REST
        self._last_trade_id:  str = ""
        self._last_1m_start: int  = 0
        self._last_5m_start: int  = 0

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Yields synthetic payloads matching the WebSocket topic format.
        Polls REST endpoints in a loop with asyncio.sleep between calls.
        """
        while True:
            try:
                # 1. Recent trades
                trades = _get("/v5/market/recent-trade", {
                    "category": "linear",
                    "symbol":   self.symbol,
                    "limit":    "50",
                })
                if trades.get("retCode") == 0:
                    yield {
                        "topic": f"publicTrade.{self.symbol}",
                        "type":  "snapshot",
                        "data":  trades["result"]["list"],
                    }

                # 2. Order book
                ob = _get("/v5/market/orderbook", {
                    "category": "linear",
                    "symbol":   self.symbol,
                    "limit":    str(self.depth_levels),
                })
                if ob.get("retCode") == 0:
                    yield {
                        "topic": f"orderbook.{self.depth_levels}.{self.symbol}",
                        "type":  "snapshot",
                        "data":  ob["result"],
                    }

                # 3. 1M kline — only yield if a new candle has closed
                k1 = _get("/v5/market/kline", {
                    "category": "linear",
                    "symbol":   self.symbol,
                    "interval": "1",
                    "limit":    "3",
                })
                if k1.get("retCode") == 0:
                    candles_1m = k1["result"]["list"]   # newest first
                    # index 1 = last CLOSED candle (index 0 = still forming)
                    if len(candles_1m) >= 2:
                        closed = candles_1m[1]
                        start  = int(closed[0])
                        if start != self._last_1m_start:
                            self._last_1m_start = start
                            yield {
                                "topic": f"kline.1.{self.symbol}",
                                "type":  "snapshot",
                                "data":  [{
                                    "start":   start,
                                    "open":    closed[1],
                                    "high":    closed[2],
                                    "low":     closed[3],
                                    "close":   closed[4],
                                    "volume":  closed[5],
                                    "confirm": True,
                                }],
                            }

                # 4. 5M kline — only yield if a new candle has closed
                k5 = _get("/v5/market/kline", {
                    "category": "linear",
                    "symbol":   self.symbol,
                    "interval": "5",
                    "limit":    "3",
                })
                if k5.get("retCode") == 0:
                    candles_5m = k5["result"]["list"]
                    if len(candles_5m) >= 2:
                        closed = candles_5m[1]
                        start  = int(closed[0])
                        if start != self._last_5m_start:
                            self._last_5m_start = start
                            yield {
                                "topic": f"kline.5.{self.symbol}",
                                "type":  "snapshot",
                                "data":  [{
                                    "start":   start,
                                    "open":    closed[1],
                                    "high":    closed[2],
                                    "low":     closed[3],
                                    "close":   closed[4],
                                    "volume":  closed[5],
                                    "confirm": True,
                                }],
                            }

            except Exception as e:
                # Log and continue — never crash on a single poll failure
                pass

            # Poll every 1 second
            await asyncio.sleep(1.0)

    @staticmethod
    def get_stream_and_data(payload: Dict[str, Any]) -> Tuple[str, Optional[dict]]:
        topic = payload.get("topic", "")
        data  = payload.get("data")
        return topic, data
