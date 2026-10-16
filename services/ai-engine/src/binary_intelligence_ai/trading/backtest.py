from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from binary_intelligence_ai.data.contracts import Candle
from binary_intelligence_ai.data.quality import validate_candles
from binary_intelligence_ai.trading.costs import PositionSide, TradingCostModel, net_return_fraction


class DirectionalBacktestReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset: str
    data_source: str
    timeframe: str
    horizon_steps: int
    observations: int
    trades: int
    flat_observations: int
    net_return_fraction: float
    maximum_drawdown_fraction: float
    win_rate: float | None
    estimated_cost_bps: float
    execution_mode: str = "paper_only"


@dataclass(frozen=True)
class DirectionalBacktestConfig:
    horizon_steps: int = 1
    fast_ema: int = 12
    slow_ema: int = 26
    costs: TradingCostModel = TradingCostModel()

    def __post_init__(self) -> None:
        if self.horizon_steps < 1:
            raise ValueError("horizon_steps must be positive")
        if not 1 <= self.fast_ema < self.slow_ema:
            raise ValueError("EMA windows must satisfy 1 <= fast_ema < slow_ema")


def run_ema_backtest(
    candles: list[Candle] | tuple[Candle, ...], config: DirectionalBacktestConfig = DirectionalBacktestConfig(),
) -> tuple[DirectionalBacktestReport, pd.DataFrame]:
    """Run a long/short/flat EMA reference strategy using closed candles only.

    This is a research baseline, not a trade recommendation or an execution
    signal. Prices are candle closes; actual fills can differ materially.
    """
    if not candles:
        raise ValueError("directional backtest requires candles")
    quality = validate_candles(
        candles, now=candles[-1].close_time, maximum_age=pd.Timedelta(seconds=candles[-1].timeframe.seconds).to_pytimedelta(),
    )
    if quality.should_abstain:
        raise ValueError(f"invalid directional backtest data: {[issue.code.value for issue in quality.issues]}")

    frame = pd.DataFrame({
        "asset": [c.asset for c in candles],
        "open_time": [c.open_time for c in candles],
        "close_time": [c.close_time for c in candles],
        "close": [float(c.close) for c in candles],
    })
    frame["ema_fast"] = frame["close"].ewm(span=config.fast_ema, adjust=False, min_periods=config.fast_ema).mean()
    frame["ema_slow"] = frame["close"].ewm(span=config.slow_ema, adjust=False, min_periods=config.slow_ema).mean()
    frame["exit_price"] = frame["close"].shift(-config.horizon_steps)
    frame["side"] = PositionSide.FLAT.value
    ready = frame[["ema_fast", "ema_slow", "exit_price"]].notna().all(axis=1)
    frame.loc[ready & (frame["ema_fast"] > frame["ema_slow"]), "side"] = PositionSide.LONG.value
    frame.loc[ready & (frame["ema_fast"] < frame["ema_slow"]), "side"] = PositionSide.SHORT.value
    frame["net_return_fraction"] = float("nan")
    for row in frame.loc[ready].itertuples():
        value = 0.0 if row.side == PositionSide.FLAT.value else float(net_return_fraction(
            side=PositionSide(row.side), entry_price=Decimal(str(row.close)), exit_price=Decimal(str(row.exit_price)), costs=config.costs,
        ))
        frame.loc[row.Index, "net_return_fraction"] = value

    evaluated = frame[ready].copy()
    trades = evaluated[evaluated["side"] != PositionSide.FLAT.value].copy()
    equity = trades["net_return_fraction"].cumsum()
    drawdown = (equity.cummax() - equity).max() if not equity.empty else 0.0
    report = DirectionalBacktestReport(
        asset=candles[0].asset,
        data_source=candles[0].source,
        timeframe=candles[0].timeframe.value,
        horizon_steps=config.horizon_steps,
        observations=len(evaluated),
        trades=len(trades),
        flat_observations=int((evaluated["side"] == PositionSide.FLAT.value).sum()),
        net_return_fraction=float(trades["net_return_fraction"].sum()) if not trades.empty else 0.0,
        maximum_drawdown_fraction=float(drawdown),
        win_rate=float((trades["net_return_fraction"] > 0).mean()) if not trades.empty else None,
        estimated_cost_bps=float(config.costs.total_bps),
    )
    return report, frame
