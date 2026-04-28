from dataclasses import dataclass, field
from typing import Iterable, List, Tuple


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


def _parse_levels(levels: Iterable[Iterable[str]]) -> List[Tuple[float, float]]:
    parsed = []
    for level in levels:
        if len(level) < 2:
            continue
        price = float(level[0])
        qty = float(level[1])
        parsed.append((price, qty))
    return parsed


def parse_depth_message(data: dict) -> OrderBookSnapshot:
    bids = _parse_levels(data.get("b", []))
    asks = _parse_levels(data.get("a", []))
    return OrderBookSnapshot(bids=bids, asks=asks, event_time=int(data.get("E", 0)))
