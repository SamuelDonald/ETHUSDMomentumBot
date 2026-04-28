from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class BinanceSettings:
    ws_base_url: str = "wss://stream.binance.com:9443/stream"
    symbol: str = "ethusdt"
    depth_levels: int = 20


@dataclass(frozen=True)
class StrategySettings:
    delta_window: int = 120
    imbalance_window: int = 60
    pressure_epsilon: float = 1e-8
    ema_period: int = 20
    ema_slope_threshold: float = 0.03
    weak_trend_multiplier: float = 0.4
    bos_lookback: int = 20
    consolidation_candles: int = 6
    consolidation_threshold_multiplier: float = 0.55
    stop_loss_buffer: float = 0.0012
    risk_reward: float = 1.5


@dataclass(frozen=True)
class BridgeSettings:
    zmq_endpoint: str = "tcp://127.0.0.1:5557"
    high_water_mark: int = 1000


@dataclass(frozen=True)
class SymbolSettings:
    canonical_symbol: str = "ETHUSD"
    broker_symbol_map: Dict[str, str] = field(
        default_factory=lambda: {
            "EXNESS": "ETHUSDm",
            "DEFAULT": "ETHUSD",
        }
    )


@dataclass(frozen=True)
class EngineSettings:
    binance: BinanceSettings = field(default_factory=BinanceSettings)
    strategy: StrategySettings = field(default_factory=StrategySettings)
    bridge: BridgeSettings = field(default_factory=BridgeSettings)
    symbols: SymbolSettings = field(default_factory=SymbolSettings)
    loop_sleep_seconds: float = 0.02


SETTINGS = EngineSettings()
