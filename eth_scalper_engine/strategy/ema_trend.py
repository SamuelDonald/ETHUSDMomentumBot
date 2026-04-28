from collections import deque
from typing import Deque, Dict


class EmaTrendFilter:
    def __init__(self, period: int = 20, slope_threshold: float = 0.03, weak_multiplier: float = 0.4):
        self.period = period
        self.slope_threshold = slope_threshold
        self.weak_threshold = slope_threshold * weak_multiplier
        self.ema_values: Deque[float] = deque(maxlen=3)
        self.last_ema: float | None = None

    def _ema(self, price: float) -> float:
        if self.last_ema is None:
            self.last_ema = price
            return price
        k = 2 / (self.period + 1)
        self.last_ema = price * k + self.last_ema * (1 - k)
        return self.last_ema

    def update(self, close_price: float) -> Dict[str, float | str]:
        ema = self._ema(close_price)
        self.ema_values.append(ema)

        if len(self.ema_values) < 2:
            return {"trend": "flat", "slope": 0.0}

        slope = self.ema_values[-1] - self.ema_values[-2]
        if slope > self.slope_threshold:
            trend = "bullish"
        elif 0 < slope <= self.slope_threshold:
            trend = "weak bullish"
        elif slope < -self.slope_threshold:
            trend = "bearish"
        elif -self.slope_threshold <= slope < 0:
            trend = "weak bearish"
        else:
            trend = "flat"

        if abs(slope) <= self.weak_threshold:
            trend = "flat"

        return {"trend": trend, "slope": slope}
