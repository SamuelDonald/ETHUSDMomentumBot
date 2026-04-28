from collections import deque
from statistics import mean
from typing import Deque

from eth_scalper_engine.data.orderbook import OrderBookSnapshot


class OrderBookImbalanceEngine:
    def __init__(self, window: int = 60):
        self.window = window
        self.bid_volumes: Deque[float] = deque(maxlen=window)
        self.ask_volumes: Deque[float] = deque(maxlen=window)

    def update(self, orderbook: OrderBookSnapshot) -> tuple[float, float]:
        bid_volume = sum(qty for _, qty in orderbook.bids)
        ask_volume = sum(qty for _, qty in orderbook.asks)
        self.bid_volumes.append(bid_volume)
        self.ask_volumes.append(ask_volume)
        return bid_volume, ask_volume

    @property
    def bid_mean(self) -> float:
        return mean(self.bid_volumes) if self.bid_volumes else 0.0

    @property
    def ask_mean(self) -> float:
        return mean(self.ask_volumes) if self.ask_volumes else 0.0
