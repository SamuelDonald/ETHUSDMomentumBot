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


class BybitOrderBook:
    def __init__(self):
        self._bids: Dict[float, float] = {}
        self._asks: Dict[float, float] = {}
        self.event_time: int = 0

    def update(self, data: dict, msg_type: str) -> "OrderBookSnapshot":
        raw_bids = data.get("b", [])
        raw_asks = data.get("a", [])

        if msg_type == "snapshot":
            self._bids = {float(p): float(q) for p, q in raw_bids if float(q) > 0}
            self._asks = {float(p): float(q) for p, q in raw_asks if float(q) > 0}
        else:
            for price, qty in raw_bids:
                p, q = float(price), float(qty)
                if q == 0:
                    self._bids.pop(p, None)
                else:
                    self._bids[p] = q
            for price, qty in raw_asks:
                p, q = float(price), float(qty)
                if q == 0:
                    self._asks.pop(p, None)
                else:
                    self._asks[p] = q

        self.event_time = int(data.get("ts", 0))
        sorted_bids = sorted(self._bids.items(), key=lambda x: -x[0])
        sorted_asks = sorted(self._asks.items(), key=lambda x:  x[0])
        return OrderBookSnapshot(
            bids=[(p, q) for p, q in sorted_bids],
            asks=[(p, q) for p, q in sorted_asks],
            event_time=self.event_time,
        )


_bybit_ob = BybitOrderBook()


def parse_depth_message(data: dict, msg_type: str = "snapshot") -> OrderBookSnapshot:
    return _bybit_ob.update(data, msg_type)
