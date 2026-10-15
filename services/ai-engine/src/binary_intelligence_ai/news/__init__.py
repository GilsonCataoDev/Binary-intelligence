"""Contexto auditável de notícias e eventos econômicos."""

from .contracts import (
    EconomicImpact,
    NewsAvailability,
    NewsContext,
    NewsEvent,
    NewsQuery,
)
from .guard import EventBlackoutConfig, NewsGuardResult, evaluate_news_guard

__all__ = [
    "EconomicImpact",
    "EventBlackoutConfig",
    "NewsAvailability",
    "NewsContext",
    "NewsEvent",
    "NewsGuardResult",
    "NewsQuery",
    "evaluate_news_guard",
]
