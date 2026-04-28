from dataclasses import dataclass

from eth_scalper_engine.core.delta_engine import DeltaEngine
from eth_scalper_engine.core.orderbook_imbalance import OrderBookImbalanceEngine


@dataclass
class PressureState:
    state: str
    delta: float
    delta_mean: float
    bid_volume: float
    ask_volume: float


class PressureEngine:
    def __init__(
        self,
        delta_engine: DeltaEngine,
        imbalance_engine: OrderBookImbalanceEngine,
        epsilon: float = 1e-8,
    ):
        self.delta_engine = delta_engine
        self.imbalance_engine = imbalance_engine
        self.epsilon = epsilon

    def evaluate(self, bid_volume: float, ask_volume: float) -> PressureState:
        delta = self.delta_engine.current_delta
        delta_mean = self.delta_engine.rolling_mean

        buyers_winning = delta > (delta_mean + self.epsilon) and bid_volume > ask_volume
        sellers_winning = delta < (delta_mean - self.epsilon) and ask_volume > bid_volume

        if buyers_winning:
            state = "bullish"
        elif sellers_winning:
            state = "bearish"
        else:
            state = "neutral"

        return PressureState(
            state=state,
            delta=delta,
            delta_mean=delta_mean,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
        )
