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
        if qty > 0:   # skip zero-quantity levels (deletions in diff stream)
            parsed.append((price, qty))
    return parsed


def parse_depth_message(data: dict) -> OrderBookSnapshot:
    # Partial book depth snapshot (@depth<N>@1000ms) uses "bids"/"asks"
    # Diff depth stream (@depth or @depth@100ms) uses "b"/"a"
    # Support both formats so the parser works regardless of stream type
    bids = _parse_levels(data.get("bids") or data.get("b", []))
    asks = _parse_levels(data.get("asks") or data.get("a", []))
    return OrderBookSnapshot(
        bids=bids,
        asks=asks,
        event_time=int(data.get("T") or data.get("E") or 0),
    )
