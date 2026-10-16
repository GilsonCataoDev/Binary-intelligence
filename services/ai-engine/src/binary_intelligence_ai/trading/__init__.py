"""Directional paper-trading research for spot FX, gold and crypto.

This module models research and simulated positions only. It has no broker or
exchange execution adapter.
"""

from .backtest import DirectionalBacktestConfig, DirectionalBacktestReport, run_ema_backtest
from .costs import TradingCostModel, net_return_fraction

__all__ = [
    "DirectionalBacktestConfig",
    "DirectionalBacktestReport",
    "TradingCostModel",
    "net_return_fraction",
    "run_ema_backtest",
]
