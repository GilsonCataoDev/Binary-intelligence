from binary_intelligence_ai.backtesting.splits import WalkForwardConfig, walk_forward_splits


def test_walk_forward_gap_purges_overlapping_horizons() -> None:
    config = WalkForwardConfig(minimum_train_size=20, test_size=10, gap=5)
    splits = list(walk_forward_splits(50, config))
    assert len(splits) == 3
    for train, test in splits:
        assert train[-1] + config.gap < test[0]
        assert set(train).isdisjoint(test)
