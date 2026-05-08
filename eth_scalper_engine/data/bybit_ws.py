"""
Bybit REST polling client — replaces WebSocket entirely.
Works through any network that allows HTTPS.
Polls every second. Order: orderbook first, then trades, then klines.
"""
import asyncio
import json
import urllib.request
from typing import Any, AsyncIterator, Dict, Optional, Tuple

BASE = "https://api.bybit.com"


def _get(path: str, params: dict) -> dict:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url   = f"{BASE}{path}?{query}"
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read())


class BybitWebSocketClient:
    def __init__(self, ws_base_url: str = BASE,
                 symbol: str = "ETHUSDT",
                 depth_levels: int = 20):
        self.symbol        = symbol.upper()
        self.depth_levels  = min(depth_levels, 50)
        self._last_1m_start = 0
        self._last_5m_start = 0

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        while True:
            try:
                # ── 1. ORDER BOOK FIRST ──────────────────────────────────────
                # Must arrive before trades so latest_orderbook is populated
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

                # ── 2. RECENT TRADES ─────────────────────────────────────────
                # Bybit REST response: list of objects with price/size/side keys
                # { execId, symbol, price, size, side, time, isBlockTrade }
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

                # ── 3. 1M KLINE ──────────────────────────────────────────────
                k1 = _get("/v5/market/kline", {
                    "category": "linear",
                    "symbol":   self.symbol,
                    "interval": "1",
                    "limit":    "3",
                })
                if k1.get("retCode") == 0:
                    candles = k1["result"]["list"]   # newest first
                    if len(candles) >= 2:
                        # index 0 = forming, index 1 = last closed
                        c     = candles[1]
                        start = int(c[0])
                        if start != self._last_1m_start:
                            self._last_1m_start = start
                            yield {
                                "topic": f"kline.1.{self.symbol}",
                                "type":  "snapshot",
                                "data":  [{
                                    "start":   start,
                                    "open":    c[1],
                                    "high":    c[2],
                                    "low":     c[3],
                                    "close":   c[4],
                                    "volume":  c[5],
                                    "confirm": True,
                                }],
                            }

                # ── 4. 5M KLINE ──────────────────────────────────────────────
                k5 = _get("/v5/market/kline", {
                    "category": "linear",
                    "symbol":   self.symbol,
                    "interval": "5",
                    "limit":    "3",
                })
                if k5.get("retCode") == 0:
                    candles = k5["result"]["list"]
                    if len(candles) >= 2:
                        c     = candles[1]
                        start = int(c[0])
                        if start != self._last_5m_start:
                            self._last_5m_start = start
                            yield {
                                "topic": f"kline.5.{self.symbol}",
                                "type":  "snapshot",
                                "data":  [{
                                    "start":   start,
                                    "open":    c[1],
                                    "high":    c[2],
                                    "low":     c[3],
                                    "close":   c[4],
                                    "volume":  c[5],
                                    "confirm": True,
                                }],
                            }

            except Exception as e:
                pass   # never crash on single poll failure

            await asyncio.sleep(1.0)

    @staticmethod
    def get_stream_and_data(payload: Dict[str, Any]) -> Tuple[str, Optional[dict]]:
        return payload.get("topic", ""), payload.get("data")
