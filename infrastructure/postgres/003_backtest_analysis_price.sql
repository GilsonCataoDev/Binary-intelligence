ALTER TABLE backtest_predictions
    ADD COLUMN IF NOT EXISTS analysis_price NUMERIC(28, 12);

UPDATE backtest_predictions
    SET analysis_price = reference_price
    WHERE analysis_price IS NULL;

ALTER TABLE backtest_predictions
    ALTER COLUMN analysis_price SET NOT NULL;
