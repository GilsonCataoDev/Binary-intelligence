import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

from binary_intelligence_ai.data.contracts import CandleQuery, DataQuality, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider
from binary_intelligence_ai.models.registry import ModelRegistry
from binary_intelligence_ai.service import AnalysisRequest, analyze_request, build_server, load_engine_configuration
from binary_intelligence_ai.service.app import EngineConfiguration

TOKEN = "t" * 40
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _payload(minutes: int = 140, data_usage: str = "transient_unvalidated") -> dict:
    candles = SimulatedCandleProvider(seed=2).get_candles(CandleQuery(
        asset="EURUSD", timeframe=Timeframe.M1, start=START, end=START + timedelta(minutes=minutes),
    ))
    return {
        "asset": "eurusd", "timeframe": "1m", "source": "simulated", "data_usage": data_usage,
        "candles": [
            {"open_time": c.open_time.isoformat(), "open": str(c.open), "high": str(c.high),
             "low": str(c.low), "close": str(c.close)}
            for c in candles
        ],
    }


@pytest.mark.parametrize("environment, message", [
    ({"ENGINE_TOKEN": "short"}, "ENGINE_TOKEN"),
    ({"ENGINE_TOKEN": TOKEN, "EXECUTION_MODE": "real"}, "EXECUTION_MODE"),
    ({"ENGINE_TOKEN": TOKEN, "REAL_EXECUTION_ENABLED": "true"}, "REAL_EXECUTION_ENABLED"),
    ({"ENGINE_TOKEN": TOKEN, "ENGINE_HOST": "0.0.0.0"}, "loopback"),
])
def test_configuration_rejects_unsafe_settings(environment: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_engine_configuration(environment)


def test_configuration_accepts_local_simulation() -> None:
    configuration = load_engine_configuration({"ENGINE_TOKEN": TOKEN})
    assert (configuration.host, configuration.port) == ("127.0.0.1", 8000)


def test_valid_series_still_abstains_without_promoted_model() -> None:
    request = AnalysisRequest.model_validate(_payload())
    result = analyze_request(request, registry=ModelRegistry(), now=START + timedelta(minutes=140))
    assert result.asset == "EURUSD"
    assert result.data_quality.status is DataQuality.VALID
    assert result.market_state is not None
    assert result.decision.value == "ABSTAIN"
    assert "no model has passed controlled promotion" in result.reasons
    assert "transient public data is not approved for model inference" in result.reasons


def test_stale_series_reports_quality_reason() -> None:
    request = AnalysisRequest.model_validate(_payload())
    result = analyze_request(request, registry=ModelRegistry(), now=START + timedelta(hours=5))
    assert result.data_quality.status is DataQuality.STALE
    assert "data quality is stale" in result.reasons


def test_request_rejects_unknown_fields_and_bad_symbols() -> None:
    with pytest.raises(ValueError):
        AnalysisRequest.model_validate({**_payload(10), "execute": True})
    with pytest.raises(ValueError):
        AnalysisRequest.model_validate({**_payload(10), "asset": "../etc"})


@pytest.fixture()
def engine_url():
    server = build_server(EngineConfiguration(host="127.0.0.1", port=0, token=TOKEN))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _post(url: str, body: bytes, token: str = TOKEN) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{url}/v1/analysis", data=body, method="POST",
        headers={"content-type": "application/json", "x-engine-token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_http_health_is_public(engine_url: str) -> None:
    with urllib.request.urlopen(f"{engine_url}/health", timeout=5) as response:
        body = json.loads(response.read())
    assert body["status"] == "ok"
    assert body["realExecutionEnabled"] is False
    assert body["model"]["approved"] is False


def test_http_analysis_requires_token(engine_url: str) -> None:
    status, body = _post(engine_url, json.dumps(_payload(10)).encode(), token="wrong")
    assert status == 401
    assert body == {"error": "unauthorized"}


def test_http_analysis_returns_abstain(engine_url: str) -> None:
    status, body = _post(engine_url, json.dumps(_payload()).encode())
    assert status == 200
    assert body["decision"] == "ABSTAIN"
    assert body["result_type"] == "analysis_only"


def test_http_analysis_rejects_invalid_input(engine_url: str) -> None:
    status, _ = _post(engine_url, b"{not json")
    assert status == 400
    status, _ = _post(engine_url, json.dumps({"asset": "EURUSD"}).encode())
    assert status == 422
    status, _ = _post(engine_url, b" " * (600 * 1024))
    assert status == 413
