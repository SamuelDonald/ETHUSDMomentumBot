import time
from typing import Dict, Optional


class SignalEngine:
    def __init__(self, rr: float = 1.5, sl_buffer: float = 0.0012):
        self.rr = rr
        self.sl_buffer = sl_buffer

    def generate(
        self,
        symbol: str,
        normalized_symbol: str,
        entry_price: float,
        pressure: str,
        trend: str,
        bos: str | None,
        market_state: str,
    ) -> Optional[Dict[str, object]]:
        if not bos or market_state != "tradable":
            return None

        buy_ok = (
            pressure == "bullish"
            and trend in {"bullish", "weak bullish"}
            and bos == "bullish"
        )
        sell_ok = (
            pressure == "bearish"
            and trend in {"bearish", "weak bearish"}
            and bos == "bearish"
        )

        if not (buy_ok or sell_ok):
            return None

        signal = "BUY" if buy_ok else "SELL"
        sl_distance = entry_price * self.sl_buffer

        if signal == "BUY":
            sl = entry_price - sl_distance
            tp = entry_price + sl_distance * self.rr
        else:
            sl = entry_price + sl_distance
            tp = entry_price - sl_distance * self.rr

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
            "timestamp": int(time.time()),
        }
