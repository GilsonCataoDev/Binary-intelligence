from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from binary_intelligence_ai import __version__
from binary_intelligence_ai.data.contracts import Candle, Timeframe
from binary_intelligence_ai.data.quality import DataQualityReport
from binary_intelligence_ai.market_analysis import analyze_market
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.models.registry import ModelRegistry
from binary_intelligence_ai.regimes import MarketState

LOGGER = logging.getLogger("binary_intelligence_ai.service")
MAX_BODY_BYTES = 512 * 1024
MAX_CANDLES = 1000
PLACEHOLDER_TOKEN = "replace_with_a_long_random_engine_secret"


@dataclass(frozen=True)
class EngineConfiguration:
    host: str
    port: int
    token: str


def load_engine_configuration(environment: Mapping[str, str] = os.environ) -> EngineConfiguration:
    token = environment.get("ENGINE_TOKEN", "")
    if len(token) < 32 or token == PLACEHOLDER_TOKEN:
        raise ValueError("ENGINE_TOKEN must be a non-placeholder secret with at least 32 characters")
    if environment.get("EXECUTION_MODE", "simulation") != "simulation":
        raise ValueError("only EXECUTION_MODE=simulation is supported")
    if environment.get("REAL_EXECUTION_ENABLED", "false").lower() != "false":
        raise ValueError("REAL_EXECUTION_ENABLED must remain false")
    host = environment.get("ENGINE_HOST", "127.0.0.1")
    if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
        raise ValueError("ENGINE_HOST must be a loopback address in this release")
    port = int(environment.get("ENGINE_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("ENGINE_PORT must be between 1 and 65535")
    return EngineConfiguration(host=host, port=port, token=token)


class CandleInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    open_time: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: str = Field(default="1.0.0", pattern=r"^1\.")
    asset: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,40}$")
    timeframe: Timeframe
    source: str = Field(min_length=1, max_length=80)
    data_usage: str = Field(pattern=r"^(transient_unvalidated|authorized_historical)$")
    candles: tuple[CandleInput, ...] = Field(max_length=MAX_CANDLES)

    @field_validator("asset")
    @classmethod
    def normalize_asset(cls, value: str) -> str:
        return value.upper()


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: str = "1.0.0"
    asset: str
    analyzed_at: datetime
    horizon_seconds: int
    decision: Decision
    reasons: tuple[str, ...]
    data_usage: str
    data_quality: DataQualityReport
    market_state: MarketState | None
    model_version: str | None
    result_type: str = "analysis_only"


def analyze_request(
    request: AnalysisRequest,
    *,
    registry: ModelRegistry,
    now: datetime | None = None,
) -> AnalysisResponse:
    analyzed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    step = timedelta(seconds=request.timeframe.seconds)
    candles = [
        Candle(
            asset=request.asset, timeframe=request.timeframe,
            open_time=item.open_time, close_time=item.open_time + step,
            open=item.open, high=item.high, low=item.low, close=item.close,
            source=request.source, ingested_at=analyzed_at,
        )
        for item in request.candles
    ]
    analysis = analyze_market(candles, now=analyzed_at, maximum_age=step * 2)

    reasons: list[str] = []
    if analysis.quality.should_abstain:
        reasons.append(f"data quality is {analysis.quality.status.value}")
    if analysis.market_state is not None and analysis.should_abstain:
        reasons.extend(analysis.market_state.reasons)
    if request.data_usage != "authorized_historical":
        reasons.append("transient public data is not approved for model inference")
    active = registry.active
    if active is None:
        reasons.append("no model has passed controlled promotion")
    else:
        # A promoted model still needs a reviewed inference path, payout and risk context.
        reasons.append("model inference path is not wired to the decision engine in this release")

    return AnalysisResponse(
        asset=request.asset,
        analyzed_at=analyzed_at,
        horizon_seconds=request.timeframe.seconds,
        decision=Decision.ABSTAIN,
        reasons=tuple(dict.fromkeys(reasons)),
        data_usage=request.data_usage,
        data_quality=analysis.quality,
        market_state=analysis.market_state,
        model_version=active.version if active else None,
    )


def build_server(configuration: EngineConfiguration, registry: ModelRegistry | None = None) -> ThreadingHTTPServer:
    model_registry = registry or ModelRegistry()
    expected_token = configuration.token.encode()

    class Handler(BaseHTTPRequestHandler):
        server_version = "BinaryIntelligenceEngine"
        sys_version = ""

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                active = model_registry.active
                self._send(HTTPStatus.OK, {
                    "status": "ok", "version": __version__, "mode": "simulation",
                    "realExecutionEnabled": False,
                    "model": {"version": active.version if active else None, "approved": active is not None},
                })
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/analysis":
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            supplied = (self.headers.get("x-engine-token") or "").encode()
            if not hmac.compare_digest(supplied, expected_token):
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            if not (self.headers.get("content-type") or "").startswith("application/json"):
                self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "expected application/json"})
                return
            try:
                length = int(self.headers.get("content-length") or "0")
            except ValueError:
                length = -1
            if length <= 0 or length > MAX_BODY_BYTES:
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE if length > MAX_BODY_BYTES else HTTPStatus.BAD_REQUEST,
                           {"error": "invalid body size"})
                return
            try:
                request = AnalysisRequest.model_validate(json.loads(self.rfile.read(length)))
                response = analyze_request(request, registry=model_registry)
            except json.JSONDecodeError:
                self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
                return
            except (ValidationError, ValueError) as error:
                self._send(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid analysis request", "detail": str(error)[:500]})
                return
            self._send(HTTPStatus.OK, response.model_dump(mode="json"))

        def _send(self, status: HTTPStatus, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            LOGGER.info("%s %s", self.address_string(), format % args)

    return ThreadingHTTPServer((configuration.host, configuration.port), Handler)
