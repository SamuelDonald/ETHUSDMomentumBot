import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, Optional, Tuple

import websockets


class BybitWebSocketClient:
    """
    Bybit V5 linear perpetuals WebSocket client.
    Replaces BinanceWebSocketClient — same interface, different protocol.

    Bybit uses a single connection with subscription messages,
    not a combined URL like Binance. After connect we send one
    subscribe message for all 4 topics, then receive a stream
    of tagged messages.

    Heartbeat: Bybit drops the connection after 10s of silence.
    We send a ping every 20s to keep it alive.
    """

    WS_URL  = "wss://stream.bybit.com/v5/public/linear"
    SYMBOL  = "ETHUSDT"

    def __init__(self, ws_base_url: str = WS_URL,
                 symbol: str = "ETHUSDT",
                 depth_levels: int = 20):
        self.symbol       = symbol.upper()
        self.depth_levels = depth_levels
        # Topics to subscribe
        self.topics = [
            f"publicTrade.{self.symbol}",
            f"orderbook.{self.depth_levels}.{self.symbol}",
            f"kline.1.{self.symbol}",
            f"kline.5.{self.symbol}",
        ]

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        backoff = 1
        while True:
            try:
                async with websockets.connect(
                    self.WS_URL,
                    ping_interval=None,     # we handle pings manually
                    max_size=10 * 1024 * 1024,
                ) as ws:
                    # Subscribe to all topics
                    sub_msg = json.dumps({"op": "subscribe", "args": self.topics})
                    await ws.send(sub_msg)
                    backoff = 1

                    last_ping = time.monotonic()

                    async for raw in ws:
                        # Send heartbeat every 20s
                        now = time.monotonic()
                        if now - last_ping > 20:
                            await ws.send(json.dumps({"op": "ping"}))
                            last_ping = now

                        payload = json.loads(raw)

                        # Skip subscription confirmations and pong responses
                        if "op" in payload:
                            continue

                        yield payload

            except Exception as e:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    @staticmethod
    def get_stream_and_data(payload: Dict[str, Any]) -> Tuple[str, Optional[dict]]:
        """
        Returns (topic, data) to match the interface expected by main.py.
        Bybit payload structure:
          { "topic": "publicTrade.ETHUSDT", "data": [...], "ts": ..., "type": "snapshot" }
        """
        topic = payload.get("topic", "")
        data  = payload.get("data")
        return topic, data
