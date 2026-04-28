from collections import deque
from statistics import mean
from typing import Deque


class DeltaEngine:
    def __init__(self, window: int = 120):
        self.window = window
        self.deltas: Deque[float] = deque(maxlen=window)

    def update_trade(self, price: float, quantity: float, is_buyer_maker: bool) -> float:
        direction = -1.0 if is_buyer_maker else 1.0
        delta = direction * quantity * price
        self.deltas.append(delta)
        return delta

    @property
    def current_delta(self) -> float:
        return self.deltas[-1] if self.deltas else 0.0

    @property
    def rolling_mean(self) -> float:
        return mean(self.deltas) if self.deltas else 0.0
