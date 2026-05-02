import asyncio
import json
from typing import Any, AsyncIterator, Dict, Optional

import websockets


class BinanceWebSocketClient:
    def __init__(self, ws_base_url: str, symbol: str, depth_levels: int = 20):
        self.symbol = symbol.lower()
        self.depth_levels = depth_levels
        # FIX: Use @depth<N> (full snapshot every 1000ms) instead of
        # @depth<N>@100ms (diff stream requiring local order book maintenance).
        # The diff stream sends only CHANGED levels — if no change occurred,
        # bids/asks arrays are empty, causing "Order book data missing" on every
        # trade tick until a meaningful update arrives.
        # Full snapshot stream always contains the top N levels — no state management needed.
        self.url = (
            f"{ws_base_url}?streams="
            f"{self.symbol}@trade/"
            f"{self.symbol}@depth{depth_levels}/"   # full snapshot, ~1s refresh
            f"{self.symbol}@kline_1m/"
            f"{self.symbol}@kline_5m"
        )

    async def stream(self) -> AsyncIterator[Dict[str, Any]]:
        backoff = 1
        while True:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=10 * 1024 * 1024,   # 10MB — depth snapshots can be large
                ) as ws:
                    backoff = 1
                    async for raw in ws:
                        payload = json.loads(raw)
                        yield payload
            except Exception as e:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    @staticmethod
    def get_stream_and_data(payload: Dict[str, Any]) -> tuple[str, Optional[dict]]:
        return payload.get("stream", ""), payload.get("data")
