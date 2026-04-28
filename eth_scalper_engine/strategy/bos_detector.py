from collections import deque
from typing import Deque, Dict


class BOSDetector:
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.candles: Deque[dict] = deque(maxlen=lookback)

    def update(self, candle: dict) -> Dict[str, float | str | None]:
        close_price = float(candle["c"])
        if len(self.candles) < 2:
            self.candles.append(candle)
            return {"bos": None, "swing_high": None, "swing_low": None}

        swing_high = max(float(c["h"]) for c in self.candles)
        swing_low = min(float(c["l"]) for c in self.candles)

        bos_state = None
        if close_price > swing_high:
            bos_state = "bullish"
        elif close_price < swing_low:
            bos_state = "bearish"

        self.candles.append(candle)
        return {"bos": bos_state, "swing_high": swing_high, "swing_low": swing_low}
