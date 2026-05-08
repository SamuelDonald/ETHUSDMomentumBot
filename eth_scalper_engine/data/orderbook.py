from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class OrderBookSnapshot:
    bids: List[Tuple[float, float]] = field(default_factory=list)
    asks: List[Tuple[float, float]] = field(default_factory=list)
    event_time: int = 0

    @property
    def best_bid(self) -> float:
        return self.bids[0][0] if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0][0] if self.asks else 0.0

    @property
    def mid_price(self) -> float:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2.0
        return self.best_bid or self.best_ask


def parse_depth_message(data: dict, msg_type: str = "snapshot") -> OrderBookSnapshot:
    """
    Bybit REST orderbook result:
    {
      "s": "ETHUSDT",
      "b": [["2000.00", "1.5"], ...],   <- bids
      "a": [["2001.00", "0.8"], ...],   <- asks
      "ts": 1234567890000,
      "u": 123
    }
    """
    raw_bids = data.get("b", [])
    raw_asks = data.get("a", [])
    ts       = int(data.get("ts", 0))

    bids = sorted(
        [(float(p), float(q)) for p, q in raw_bids if float(q) > 0],
        key=lambda x: -x[0]
    )
    asks = sorted(
        [(float(p), float(q)) for p, q in raw_asks if float(q) > 0],
        key=lambda x:  x[0]
    )

    return OrderBookSnapshot(bids=bids, asks=asks, event_time=ts)
