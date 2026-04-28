from collections import deque
from typing import Deque, Dict


class BOSDetector:
    def __init__(self, lookback: int = 2):
        self.lookback = lookback
        self.window: Deque[dict] = deque(maxlen=(lookback * 2) + 1)
        self.last_swing_high: float | None = None
        self.last_swing_low: float | None = None

    def update(self, candle: dict) -> Dict[str, float | str | None]:
        self.window.append(candle)

        if len(self.window) == self.window.maxlen:
            center_idx = self.lookback
            center = self.window[center_idx]
            center_high = float(center["h"])
            center_low = float(center["l"])

            left = list(self.window)[:center_idx]
            right = list(self.window)[center_idx + 1 :]

            if all(center_high > float(c["h"]) for c in left + right):
                self.last_swing_high = center_high

            if all(center_low < float(c["l"]) for c in left + right):
                self.last_swing_low = center_low

        close_price = float(candle["c"])
        bos_state = None

        if self.last_swing_high is not None and close_price > self.last_swing_high:
            bos_state = "bullish"
        elif self.last_swing_low is not None and close_price < self.last_swing_low:
            bos_state = "bearish"

        return {
            "bos": bos_state,
            "swing_high": self.last_swing_high,
            "swing_low": self.last_swing_low,
        }
