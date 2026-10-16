from datetime import datetime, timedelta, timezone
from decimal import Decimal

from binary_intelligence_ai.data.contracts import Candle, Timeframe
from binary_intelligence_ai.trading import DirectionalBacktestConfig, TradingCostModel, net_return_fraction, run_ema_backtest
from binary_intelligence_ai.trading.costs import PositionSide


def test_net_return_applies_direction_and_all_explicit_costs() -> None:
    costs = TradingCostModel(spread_bps=Decimal("2"), slippage_bps=Decimal("1"), commission_bps=Decimal("1"))
    assert net_return_fraction(
        side=PositionSide.LONG, entry_price=Decimal("100"), exit_price=Decimal("101"), costs=costs,
    ) == Decimal("0.0096")
    assert net_return_fraction(
        side=PositionSide.SHORT, entry_price=Decimal("100"), exit_price=Decimal("99"), costs=costs,
    ) == Decimal("0.0096")


def test_ema_backtest_keeps_flat_rows_and_reports_paper_only() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for index in range(20):
        open_price = Decimal("100") + Decimal(index)
        candles.append(Candle(
            asset="BTCUSDT", timeframe=Timeframe.M5,
            open_time=start + timedelta(minutes=5 * index), close_time=start + timedelta(minutes=5 * (index + 1)),
            open=open_price, high=open_price + 1, low=open_price - 1, close=open_price + Decimal("0.5"),
            volume=Decimal("1"), source="FIXTURE", ingested_at=start,
        ))

    report, records = run_ema_backtest(candles, DirectionalBacktestConfig(
        fast_ema=3, slow_ema=5, costs=TradingCostModel(spread_bps=Decimal("2")),
    ))
    assert report.asset == "BTCUSDT"
    assert report.execution_mode == "paper_only"
    assert report.trades > 0
    assert report.estimated_cost_bps == 2.0
    assert set(records["side"].dropna()) <= {"long", "short", "flat"}
