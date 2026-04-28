import asyncio
import json
from typing import Any, AsyncIterator, Dict, Optional

import websockets


class BinanceWebSocketClient:
    def __init__(self, ws_base_url: str, symbol: str, depth_levels: int = 20):
        self.symbol = symbol.lower()
        self.depth_levels = depth_levels
        self.url = (
            f"{ws_base_url}?streams="
            f"{self.symbol}@trade/{self.symbol}@depth{depth_levels}@100ms/"
            f"{self.symbol}@kline_1m/{self.symbol}@kline_5m"
        )

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        backoff = 1
        while True:
            try:
                async with websockets.connect(self.url, ping_interval=20, ping_timeout=20) as ws:
                    backoff = 1
                    async for raw in ws:
                        payload = json.loads(raw)
                        yield payload
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    @staticmethod
    def get_stream_and_data(payload: Dict[str, Any]) -> tuple[str, Optional[dict]]:
        return payload.get("stream", ""), payload.get("data")
