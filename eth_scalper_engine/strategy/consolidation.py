from collections import deque
from statistics import mean
from typing import Deque, Dict


class ConsolidationFilter:
    def __init__(self, candles: int = 6, threshold_multiplier: float = 0.55):
        self.candles = candles
        self.threshold_multiplier = threshold_multiplier
        self.ranges: Deque[float] = deque(maxlen=150)
        self.last_candles: Deque[dict] = deque(maxlen=candles)

    def update(self, candle: dict) -> Dict[str, float | str]:
        high = float(candle["h"])
        low = float(candle["l"])
        candle_range = high - low

        self.ranges.append(candle_range)
        self.last_candles.append(candle)

        if len(self.last_candles) < self.candles:
            return {"state": "tradable", "range": candle_range, "threshold": 0.0}

        recent_high = max(float(c["h"]) for c in self.last_candles)
        recent_low = min(float(c["l"]) for c in self.last_candles)
        rolling_six_range = recent_high - recent_low

        base_threshold = mean(self.ranges) if self.ranges else rolling_six_range
        dynamic_threshold = base_threshold * self.threshold_multiplier

        state = "consolidating" if rolling_six_range < dynamic_threshold else "tradable"
        return {"state": state, "range": rolling_six_range, "threshold": dynamic_threshold}
