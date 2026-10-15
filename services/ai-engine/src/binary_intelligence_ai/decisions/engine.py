from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from binary_intelligence_ai.data.contracts import DataQuality
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.models.inference import InferenceResult
from binary_intelligence_ai.news.guard import NewsGuardResult


class DecisionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    inference: InferenceResult
    payout: float = Field(gt=0, le=1)
    payout_is_current: bool
    model_approved: bool
    news_guard: NewsGuardResult
    risk_allowed: bool
    risk_reasons: tuple[str, ...] = ()
    volatility_extreme: bool = False


class DecisionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: Decision
    payout: float = Field(gt=0, le=1)
    probability_used: float = Field(ge=0, le=1)
    expected_value: float | None
    break_even_probability: float
    reasons: tuple[str, ...]


def decide(context: DecisionContext) -> DecisionOutcome:
    blockers: list[str] = []
    inference = context.inference
    if inference.data_quality != DataQuality.VALID:
        blockers.append(f"data quality is {inference.data_quality.value}")
    if not inference.confidence_calibrated:
        blockers.append("model probabilities are not calibrated")
    if not context.model_approved:
        blockers.append("model is not approved")
    if not context.payout_is_current:
        blockers.append("current payout is unavailable")
    if context.news_guard.blocked:
        blockers.extend(context.news_guard.reasons)
    if not context.risk_allowed:
        blockers.extend(context.risk_reasons or ("risk controls rejected the operation",))
    if context.volatility_extreme:
        blockers.append("extreme volatility safety block")

    threshold = 1 / (1 + context.payout)
    direction = Decision.CALL if inference.probability_up >= inference.probability_down else Decision.PUT
    probability = inference.probability_up if direction == Decision.CALL else inference.probability_down
    expected_value = probability * context.payout - (1 - probability)
    if expected_value <= 0:
        blockers.append("estimated value is not positive at the current payout")

    if blockers:
        return DecisionOutcome(
            decision=Decision.ABSTAIN,
            payout=context.payout,
            probability_used=probability,
            expected_value=expected_value,
            break_even_probability=threshold,
            reasons=tuple(dict.fromkeys(blockers)),
        )
    return DecisionOutcome(
        decision=direction,
        payout=context.payout,
        probability_used=probability,
        expected_value=expected_value,
        break_even_probability=threshold,
        reasons=("positive expected value after deterministic safety checks",),
    )
