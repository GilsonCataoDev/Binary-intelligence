"""Teste de viabilidade com dados públicos da Deriv mantidos apenas em memória.

Nenhum preço é gravado em disco: a saída contém somente métricas agregadas.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pandas as pd

from binary_intelligence_ai.backtesting.labels import SettlementRule
from binary_intelligence_ai.backtesting.metrics import TiePolicy
from binary_intelligence_ai.backtesting.runner import (
    BacktestConfig,
    BacktestRun,
    build_backtest_run,
    prediction_records,
    prepare_backtest_dataset,
)
from binary_intelligence_ai.backtesting.splits import WalkForwardConfig, walk_forward_splits
from binary_intelligence_ai.data.contracts import Candle, Timeframe
from binary_intelligence_ai.models import FrequencyBaseline, TechnicalRuleBaseline
from binary_intelligence_ai.models.baselines import break_even_probability
from binary_intelligence_ai.models.candidates import DEFAULT_CANDIDATES, CalibrationConfig, CalibratedCandidate
from binary_intelligence_ai.models.evaluation import _decisions
from binary_intelligence_ai.models.promotion import assess_candidate

DERIV_PUBLIC_WS = "wss://api.derivws.com/trading/v1/options/ws/public"
PAGE_SIZE = 1000
MINIMUM_SEGMENT = 300


@dataclass(frozen=True)
class ViabilityConfig:
    horizon_minutes: int
    payout: float
    tie_policy: TiePolicy = TiePolicy.LOSS
    minimum_train_size: int = 5000
    test_size: int = 2000


async def fetch_m1_candles(symbol: str, days: int) -> list[dict[str, Any]]:
    import websockets

    start = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    by_epoch: dict[int, dict[str, Any]] = {}
    end: int | str = "latest"
    empty_pages = 0
    async with websockets.connect(DERIV_PUBLIC_WS, open_timeout=10) as ws:
        while True:
            await ws.send(json.dumps({
                "ticks_history": symbol, "style": "candles", "granularity": 60, "count": PAGE_SIZE, "end": end,
            }))
            response = json.loads(await ws.recv())
            if "error" in response:
                raise RuntimeError(f"Deriv rejected history request: {response['error'].get('message')}")
            batch = response.get("candles") or []
            new = [c for c in batch if int(c["epoch"]) not in by_epoch and int(c["epoch"]) >= start]
            for candle in new:
                by_epoch[int(candle["epoch"])] = candle
            if not new:
                # An end inside a market closure returns nothing; step back past the closure.
                empty_pages += 1
                if end == "latest" or empty_pages > 16:
                    break
                end = int(end) - 6 * 3600
                if end <= start:
                    break
                continue
            empty_pages = 0
            oldest = min(int(c["epoch"]) for c in new)
            if oldest <= start:
                break
            end = oldest - 1
            print(f"  {len(by_epoch)} candles carregados...", file=sys.stderr)
            await asyncio.sleep(0.3)
    return [by_epoch[key] for key in sorted(by_epoch)]


async def fetch_net_payout(symbol: str, minutes: int) -> float | None:
    import websockets

    async with websockets.connect(DERIV_PUBLIC_WS, open_timeout=10) as ws:
        await ws.send(json.dumps({
            "proposal": 1, "amount": 1, "basis": "stake", "contract_type": "CALL", "currency": "USD",
            "duration": minutes, "duration_unit": "m", "underlying_symbol": symbol,
        }))
        response = json.loads(await ws.recv())
    return net_payout_from_proposal(response)


def net_payout_from_proposal(response: dict[str, Any]) -> float | None:
    proposal = response.get("proposal") or {}
    ask, payout = proposal.get("ask_price"), proposal.get("payout")
    if "error" in response or not ask or not payout:
        return None
    return round((float(payout) - float(ask)) / float(ask), 6)


def contiguous_segments(raw: list[dict[str, Any]], *, symbol: str, now: datetime) -> list[list[Candle]]:
    step = timedelta(minutes=1)
    segments: list[list[Candle]] = []
    current: list[Candle] = []
    for item in raw:
        open_time = datetime.fromtimestamp(int(item["epoch"]), timezone.utc)
        if open_time + step > now:
            continue
        candle = Candle(
            asset=symbol, timeframe=Timeframe.M1, open_time=open_time, close_time=open_time + step,
            open=Decimal(str(item["open"])), high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])), close=Decimal(str(item["close"])),
            source="deriv_public_transient", ingested_at=now,
        )
        if current and candle.open_time != current[-1].close_time:
            segments.append(current)
            current = []
        current.append(candle)
    if current:
        segments.append(current)
    return [segment for segment in segments if len(segment) >= MINIMUM_SEGMENT]


def run_viability(segments: list[list[Candle]], config: ViabilityConfig) -> dict[str, Any]:
    if not segments:
        raise ValueError("no contiguous segment is long enough")
    backtest = BacktestConfig(
        settlement=SettlementRule(horizon_steps=config.horizon_minutes),
        walk_forward=WalkForwardConfig(
            minimum_train_size=config.minimum_train_size, test_size=config.test_size, gap=config.horizon_minutes,
        ),
        payout=config.payout,
        tie_policy=config.tie_policy,
    )
    # Labels are built per segment so no outcome crosses a market closure.
    dataset = pd.concat([prepare_backtest_dataset(s, backtest) for s in segments], ignore_index=True)
    splits = list(walk_forward_splits(len(dataset), backtest.walk_forward))
    if not splits:
        raise ValueError(f"only {len(dataset)} labeled rows; not enough for walk-forward")

    parts: dict[str, list[pd.DataFrame]] = {"frequency": [], "technical_rule": []}
    parts.update({spec.version: [] for spec in DEFAULT_CANDIDATES})
    technical = TechnicalRuleBaseline()
    for fold, (train_index, test_index) in enumerate(splits):
        train, test = dataset.iloc[train_index], dataset.iloc[test_index].copy()
        frequency = FrequencyBaseline()
        frequency.fit(train["outcome"])
        probability, decision = frequency.predict(len(test), payout=config.payout)
        parts["frequency"].append(prediction_records(test, probability, decision, fold))
        probability, decision = technical.predict(test)
        parts["technical_rule"].append(prediction_records(test, probability, decision, fold))
        for spec in DEFAULT_CANDIDATES:
            candidate = CalibratedCandidate(
                spec, calibration=CalibrationConfig(gap=config.horizon_minutes), random_state=2026 + fold,
            )
            candidate.fit(train)
            probability = candidate.predict_probability_up(test)
            parts[spec.version].append(
                prediction_records(test, probability, _decisions(probability, payout=config.payout), fold)
            )

    runs: dict[str, BacktestRun] = {
        name: build_backtest_run(name, pd.concat(chunks), segments[0], backtest, len(splits))
        for name, chunks in parts.items()
    }
    baseline = runs["frequency"]
    strategies = {}
    for name, run in runs.items():
        metrics = run.report.metrics
        entry: dict[str, Any] = {
            "operations": metrics.operations,
            "hit_rate": metrics.hit_rate,
            "hit_rate_ci95": metrics.hit_rate_ci95,
            "net_return_units": metrics.net_return_units,
            "expectation_per_operation": metrics.expectation_per_operation,
            "maximum_drawdown_units": metrics.maximum_drawdown_units,
            "brier_score": metrics.brier_score,
        }
        if name not in ("frequency", "technical_rule"):
            assessment = assess_candidate(baseline, run)
            # Holdout is a separate promotion step; report the statistical criteria on their own.
            entry["statistical_failures"] = [
                reason for reason in assessment.reasons if "holdout" not in reason
            ]
        strategies[name] = entry

    up_share = float((dataset["outcome"] == "up").mean())
    return {
        "observations_out_of_sample": int(sum(len(test) for _, test in splits)),
        "labeled_rows": int(len(dataset)),
        "folds": len(splits),
        "segments": len(segments),
        "period_utc": [segments[0][0].open_time.isoformat(), segments[-1][-1].close_time.isoformat()],
        "horizon_minutes": config.horizon_minutes,
        "net_payout": config.payout,
        "break_even_hit_rate": break_even_probability(config.payout),
        "tie_policy": config.tie_policy.value,
        "share_of_up_outcomes": up_share,
        "strategies": strategies,
        "verdict": _verdict(strategies, break_even_probability(config.payout)),
    }


def _verdict(strategies: dict[str, Any], break_even: float) -> str:
    viable = [
        name for name, entry in strategies.items()
        if entry.get("statistical_failures") == [] and entry["hit_rate_ci95"] and entry["hit_rate_ci95"][0] > break_even
    ]
    if viable:
        return f"candidates passing statistical criteria (still need untouched holdout): {', '.join(viable)}"
    return "no strategy shows a statistically reliable edge above break-even"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Viability test on transient Deriv public data (in memory only).")
    parser.add_argument("--symbol", default="R_100")
    parser.add_argument("--horizon-minutes", type=int, default=5)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--payout", type=float, help="net payout fraction; default: current Deriv quote")
    parser.add_argument("--tie-policy", choices=[p.value for p in TiePolicy], default=TiePolicy.LOSS.value)
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 90:
        parser.error("--days must be between 1 and 90")

    payout = args.payout
    if payout is None:
        payout = asyncio.run(fetch_net_payout(args.symbol, args.horizon_minutes))
        if payout is None:
            parser.error(f"Deriv does not quote {args.symbol} for {args.horizon_minutes} minutes; pass --payout")
    print(f"Baixando {args.days} dias de candles M1 de {args.symbol} (somente em memoria)...", file=sys.stderr)
    raw = asyncio.run(fetch_m1_candles(args.symbol, args.days))
    segments = contiguous_segments(raw, symbol=args.symbol, now=datetime.now(timezone.utc))
    del raw
    print(f"Avaliando {sum(map(len, segments))} candles em {len(segments)} trecho(s) continuo(s)...", file=sys.stderr)
    result = run_viability(segments, ViabilityConfig(
        horizon_minutes=args.horizon_minutes, payout=payout, tie_policy=TiePolicy(args.tie_policy),
    ))
    result = {"symbol": args.symbol, "data_usage": "transient_in_memory_only", "payout_source":
              "current Deriv quote (snapshot)" if args.payout is None else "user supplied", **result}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
