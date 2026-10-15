from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.backtesting import BacktestConfig, compare_baselines
from binary_intelligence_ai.backtesting.runner import prepare_backtest_dataset
from binary_intelligence_ai.backtesting.splits import WalkForwardConfig
from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider
from binary_intelligence_ai.models.candidates import (
    CalibrationConfig,
    CalibratedCandidate,
    CandidateKind,
    CandidateSpec,
)
from binary_intelligence_ai.models.evaluation import ModelEvaluationConfig, evaluate_model_candidates
from binary_intelligence_ai.models.promotion import assess_candidate


def _candles(count: int = 750):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimulatedCandleProvider(seed=99).get_candles(CandleQuery(
        asset="EURUSD", timeframe=Timeframe.M1, start=start, end=start + timedelta(minutes=count)
    ))


def _config() -> BacktestConfig:
    return BacktestConfig(walk_forward=WalkForwardConfig(minimum_train_size=500, test_size=100, gap=5))


def test_calibration_period_is_strictly_after_base_training_period() -> None:
    dataset = prepare_backtest_dataset(_candles(), _config())
    candidate = CalibratedCandidate(
        CandidateSpec(CandidateKind.LOGISTIC, "logistic-test"),
        calibration=CalibrationConfig(fraction=0.2, gap=5),
    )
    candidate.fit(dataset.iloc[:500])
    assert candidate.training_end is not None
    assert candidate.calibration_start is not None
    assert candidate.training_end < candidate.calibration_start
    assert candidate.training_rows > candidate.calibration_rows >= 40


def test_all_candidates_produce_calibrated_out_of_sample_probabilities() -> None:
    runs = evaluate_model_candidates(_candles(), backtest=_config())
    assert set(runs) == {"logistic-v1", "random-forest-v1", "histogram-boosting-v1"}
    for run in runs.values():
        assert run.records["probability_up"].between(0, 1).all()
        assert run.report.metrics.brier_score is not None
        assert run.report.metrics.log_loss is not None


def test_promotion_is_an_explicit_assessment_against_frequency_baseline() -> None:
    candles = _candles()
    config = _config()
    baseline = compare_baselines(candles, config)["frequency"]
    candidate = evaluate_model_candidates(
        candles,
        backtest=config,
        evaluation=ModelEvaluationConfig(candidates=(CandidateSpec(CandidateKind.LOGISTIC, "logistic-test"),)),
    )["logistic-test"]
    assessment = assess_candidate(baseline, candidate)
    assert assessment.baseline == "frequency"
    assert assessment.candidate == "logistic-test"
    assert assessment.approved is False
    assert assessment.holdout_confirmed is False
    assert "untouched holdout evaluation pipeline has not been implemented" in assessment.reasons


def test_promotion_rejects_runs_with_different_evaluation_configuration() -> None:
    candles = _candles()
    baseline = compare_baselines(candles, _config())["frequency"]
    different = BacktestConfig(
        payout=0.7,
        walk_forward=WalkForwardConfig(minimum_train_size=500, test_size=100, gap=5),
    )
    candidate = evaluate_model_candidates(
        candles,
        backtest=different,
        evaluation=ModelEvaluationConfig(candidates=(CandidateSpec(CandidateKind.LOGISTIC, "logistic-test"),)),
    )["logistic-test"]

    assessment = assess_candidate(baseline, candidate)

    assert not assessment.approved
    assert any("payout differs" in reason for reason in assessment.reasons)
