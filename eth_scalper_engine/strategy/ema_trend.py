from typing import Dict


class EmaTrendFilter:
    def __init__(self, period: int = 20, slope_threshold: float = 0.03):
        self.period = period
        self.slope_threshold = slope_threshold
        self.last_ema: float | None = None
        self.previous_ema: float | None = None
        self.candle_count: int = 0

    def _ema(self, close_price: float) -> float:
        if self.last_ema is None:
            self.last_ema = close_price
            return close_price
        k = 2 / (self.period + 1)
        self.last_ema = close_price * k + self.last_ema * (1 - k)
        return self.last_ema

    def update(self, candle: dict) -> Dict[str, float | str]:
        close_price = float(candle["c"])
        ema_current = self._ema(close_price)
        self.candle_count += 1

        if self.candle_count < self.period:
            self.previous_ema = ema_current
            return {"trend": "flat", "slope": 0.0}

        if self.previous_ema is None:
            self.previous_ema = ema_current
            return {"trend": "flat", "slope": 0.0}

        slope = ema_current - self.previous_ema
        self.previous_ema = ema_current

        if slope > self.slope_threshold:
            trend = "bullish"
        elif slope < -self.slope_threshold:
            trend = "bearish"
        else:
            trend = "flat"

        return {"trend": trend, "slope": slope}
