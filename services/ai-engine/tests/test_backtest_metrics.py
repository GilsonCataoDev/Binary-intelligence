import pandas as pd

from binary_intelligence_ai.backtesting.metrics import TiePolicy, evaluate_records


def test_metrics_apply_payout_ties_and_drawdown() -> None:
    records = pd.DataFrame({
        "decision": ["CALL", "PUT", "PUT", "ABSTAIN"],
        "outcome": ["up", "up", "tie", "down"],
        "probability_up": [0.8, 0.2, 0.5, 0.4],
        "hour": [9, 9, 10, 10],
        "market_regime": ["trending_up", "trending_down", "ranging", "ranging"],
    })
    metrics = evaluate_records(records, payout=0.8, tie_policy=TiePolicy.PUSH)
    assert metrics.operations == 3
    assert (metrics.wins, metrics.losses, metrics.ties) == (1, 1, 1)
    assert metrics.hit_rate == 0.5
    assert metrics.net_return_units == -0.2
    assert metrics.maximum_drawdown_units == 1.0
    assert metrics.payout_sensitivity["0.70"] == -0.3


def test_tie_can_be_configured_as_loss() -> None:
    records = pd.DataFrame({
        "decision": ["CALL"], "outcome": ["tie"], "probability_up": [0.5]
    })
    metrics = evaluate_records(records, payout=0.8, tie_policy=TiePolicy.LOSS)
    assert metrics.net_return_units == -1.0
