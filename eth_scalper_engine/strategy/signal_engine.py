import math
import time
from typing import Dict, Optional


class SignalEngine:
    def __init__(self, rr: float = 1.5, signal_cooldown: int = 5, max_signal_age: int = 2):
        self.rr = rr
        self.signal_cooldown = signal_cooldown
        self.max_signal_age = max_signal_age
        self.last_signal_time: int = 0
        self.last_signal_type: str | None = None

    def generate(
        self,
        symbol: str,
        normalized_symbol: str,
        entry_price: float,
        pressure: str,
        trend: str,
        bos: str | None,
        market_state: str,
        swing_high: float | None,
        swing_low: float | None,
        signal_time: int,
    ) -> Optional[Dict[str, object]]:
        now = int(time.time())
        if (now - signal_time) > self.max_signal_age:
            return None

        if not bos or market_state != "tradable":
            return None

        buy_ok = pressure == "bullish" and trend == "bullish" and bos == "bullish"
        sell_ok = pressure == "bearish" and trend == "bearish" and bos == "bearish"

        if not (buy_ok or sell_ok):
            return None

        signal = "BUY" if buy_ok else "SELL"
        if self.last_signal_type == signal and (now - self.last_signal_time) < self.signal_cooldown:
            return None

        if signal == "BUY":
            sl = swing_low
            if sl is None:
                return None
            tp = entry_price + (entry_price - sl) * self.rr
        else:
            sl = swing_high
            if sl is None:
                return None
            tp = entry_price - (sl - entry_price) * self.rr

        if not self._is_valid_signal(entry_price=entry_price, sl=sl, tp=tp, signal=signal):
            return None

        self.last_signal_time = now
        self.last_signal_type = signal

        return {
            "symbol": symbol,
            "normalized_symbol": normalized_symbol,
            "signal": signal,
            "entry": entry_price,
            "sl": sl,
            "tp": tp,
            "rr": self.rr,
            "pressure": pressure,
            "trend": trend,
            "bos": bos,
            "market_state": market_state,
            "timestamp": now,
        }

    def _is_valid_signal(self, entry_price: float, sl: float, tp: float, signal: str) -> bool:
        values = (entry_price, sl, tp)
        if any(v is None or math.isnan(v) for v in values):
            return False
        if sl == entry_price or tp == entry_price:
            return False
        if signal not in {"BUY", "SELL"}:
            return False
        return True
