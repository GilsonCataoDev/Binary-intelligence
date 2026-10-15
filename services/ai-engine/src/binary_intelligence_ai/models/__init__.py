"""Baselines, candidatos calibrados e contratos de inferência."""

from .baselines import Decision, FrequencyBaseline, TechnicalRuleBaseline
from .candidates import CandidateKind, CandidateSpec, CalibratedCandidate, MODEL_FEATURES
from .inference import InferenceResult

__all__ = [
    "Decision", "FrequencyBaseline", "TechnicalRuleBaseline", "CandidateKind",
    "CandidateSpec", "CalibratedCandidate", "InferenceResult", "MODEL_FEATURES",
]
