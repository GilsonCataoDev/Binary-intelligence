from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np


@dataclass(frozen=True)
class WalkForwardConfig:
    minimum_train_size: int = 200
    test_size: int = 50
    gap: int = 5

    def __post_init__(self) -> None:
        if self.minimum_train_size < 1 or self.test_size < 1 or self.gap < 0:
            raise ValueError("walk-forward sizes must be positive and gap cannot be negative")


def walk_forward_splits(sample_count: int, config: WalkForwardConfig) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    train_end = config.minimum_train_size
    while train_end + config.gap < sample_count:
        test_start = train_end + config.gap
        test_end = min(test_start + config.test_size, sample_count)
        if test_start >= test_end:
            return
        yield np.arange(0, train_end), np.arange(test_start, test_end)
        train_end += config.test_size
