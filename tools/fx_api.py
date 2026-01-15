from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from namel3ss_safeio import safe_env_get, safe_open, safe_urlopen

from tools.shared import api_cache, api_resilience


PRIMARY_ENV = "FX_API_KEY"
SECONDARY_ENV = "FX_API_SECONDARY_KEY"
FORCE_FAIL_ENV = "FX_API_FORCE_FAIL"

PRIMARY_URL = "https://openexchangerates.org/api/latest.json"
SECONDARY_URL = "https://api.exchangerate.host/latest"

CACHE_TTL_SECONDS = 12 * 60 * 60
TIMEOUT_SECONDS = 8
RETRY_POLICY = api_resilience.RetryPolicy(max_attempts=3, base_delay=0.2, max_delay=1.0)
CIRCUIT_FAILURE_THRESHOLD = 2
CIRCUIT_OPEN_SECONDS = 60

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "fx_eur_usd.json"
MOCK_UPDATED_AT = "2024-01-01T00:00:00Z"
MOCK_RATES = {
    "EUR/USD": 1.08,
    "USD/EUR": 0.93,
    "GBP/USD": 1.27,
    "USD/GBP": 0.79,
}


def run(payload: dict[str, Any]) -> dict[str, Any]:
    from_code = _normalize_code(payload.get("from"))
    to_code = _normalize_code(payload.get("to"))
    primary_key = safe_env_get(PRIMARY_ENV)
    secondary_key = safe_env_get(SECONDARY_ENV)
    if not (primary_key or secondary_key):
        return _mock_response(from_code, to_code)
    now = api_cache.now_timestamp()
    cache_key = f"fx:{from_code}:{to_code}"
    pair = f"{from_code}/{to_code}"
    providers = [
        ("primary", primary_key, lambda: _fetch_primary(from_code, to_code, primary_key)),
        ("secondary", secondary_key, lambda: _fetch_secondary(from_code, to_code)),
    ]
    for name, token, fetcher in providers:
        if not token:
            continue
        rate = _attempt_provider(name, fetcher, now)
        if rate is None:
            continue
        entry = api_cache.set_response(cache_key, {"pair": pair, "rate": rate}, updated_ts=now)
        return {
            "pair": pair,
            "rate": rate,
            "source": "api",
            "last_updated": entry.updated_at,
            "stale": False,
        }

    cached = api_cache.get_response(cache_key)
    if cached:
        cached_pair, cached_rate = _payload_rate(cached.payload, pair)
        if cached_rate is not None:
            stale = not api_cache.is_fresh(cached, CACHE_TTL_SECONDS, now=now)
            return {
                "pair": cached_pair,
                "rate": cached_rate,
                "source": "cache",
                "last_updated": cached.updated_at,
                "stale": stale,
            }

    fixture = _load_fixture(pair)
    if fixture is not None:
        return {
            "pair": fixture["pair"],
            "rate": fixture["rate"],
            "source": "fixture",
            "last_updated": fixture["last_updated"],
            "stale": False,
        }

    return _mock_response(from_code, to_code)


def _normalize_code(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return "USD"


def _attempt_provider(name: str, fetcher, now: float) -> float | None:
    if _force_fail():
        api_cache.record_failure(
            _circuit_key(name),
            now=now,
            threshold=CIRCUIT_FAILURE_THRESHOLD,
            open_seconds=CIRCUIT_OPEN_SECONDS,
        )
        return None
    if api_cache.is_circuit_open(_circuit_key(name), now=now):
        return None
    try:
        rate = api_resilience.call_with_retries(fetcher, RETRY_POLICY)
    except Exception:
        api_cache.record_failure(
            _circuit_key(name),
            now=now,
            threshold=CIRCUIT_FAILURE_THRESHOLD,
            open_seconds=CIRCUIT_OPEN_SECONDS,
        )
        return None
    api_cache.record_success(_circuit_key(name))
    return rate


def _circuit_key(provider: str) -> str:
    return f"fx:{provider}"


def _force_fail() -> bool:
    value = safe_env_get(FORCE_FAIL_ENV)
    return isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}


def _fetch_primary(from_code: str, to_code: str, api_key: str | None) -> float:
    if not api_key:
        raise ValueError("Missing primary API key")
    params = {
        "app_id": api_key,
        "symbols": ",".join(sorted({from_code, to_code})),
    }
    url = f"{PRIMARY_URL}?{parse.urlencode(params)}"
    data = _read_json(url)
    rates = data.get("rates") if isinstance(data, dict) else None
    if not isinstance(rates, dict):
        raise ValueError("FX API returned no rates")
    rate = _cross_rate(from_code, to_code, rates)
    if rate <= 0:
        raise ValueError("FX API returned invalid rate")
    return rate


def _fetch_secondary(from_code: str, to_code: str) -> float:
    params = {
        "base": from_code,
        "symbols": to_code,
    }
    url = f"{SECONDARY_URL}?{parse.urlencode(params)}"
    data = _read_json(url)
    rates = data.get("rates") if isinstance(data, dict) else None
    if not isinstance(rates, dict):
        raise ValueError("Secondary FX API returned no rates")
    rate = rates.get(to_code)
    if not isinstance(rate, (int, float)):
        raise ValueError("Secondary FX API returned invalid rate")
    return float(rate)


def _read_json(url: str) -> Any:
    req = request.Request(url, headers={"Accept": "application/json"})
    try:
        with safe_urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as err:
        if err.code == 429 or 500 <= err.code <= 599:
            raise api_resilience.TransientAPIError(str(err), status_code=err.code) from err
        raise
    except (error.URLError, TimeoutError) as err:
        raise api_resilience.TransientAPIError(str(err)) from err
    return json.loads(raw)


def _cross_rate(from_code: str, to_code: str, rates: dict[str, Any]) -> float:
    if from_code == to_code:
        return 1.0
    if from_code == "USD":
        to_rate = rates.get(to_code)
        if to_rate is None:
            raise ValueError("Missing target rate")
        return float(to_rate)
    if to_code == "USD":
        from_rate = rates.get(from_code)
        if from_rate is None:
            raise ValueError("Missing base rate")
        return 1.0 / float(from_rate)
    from_rate = rates.get(from_code)
    to_rate = rates.get(to_code)
    if from_rate is None or to_rate is None:
        raise ValueError("Missing rates for pair")
    return float(to_rate) / float(from_rate)


def _payload_rate(payload: Any, pair: str) -> tuple[str, float | None]:
    if isinstance(payload, dict):
        cached_rate = payload.get("rate")
        cached_pair = payload.get("pair")
        if isinstance(cached_rate, (int, float)):
            pair_value = cached_pair if isinstance(cached_pair, str) else pair
            return pair_value, float(cached_rate)
    return pair, None


def _load_fixture(pair: str) -> dict[str, Any] | None:
    if pair != "EUR/USD":
        return None
    if not FIXTURE_PATH.exists():
        return None
    try:
        with safe_open(FIXTURE_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    rate = data.get("rate")
    last_updated = data.get("last_updated")
    fixture_pair = data.get("pair")
    if not isinstance(rate, (int, float)) or not isinstance(last_updated, str):
        return None
    if not isinstance(fixture_pair, str):
        fixture_pair = pair
    return {"pair": fixture_pair, "rate": float(rate), "last_updated": last_updated}


def _mock_response(from_code: str, to_code: str) -> dict[str, Any]:
    pair = f"{from_code}/{to_code}"
    rate = MOCK_RATES.get(pair, 1.0)
    return {
        "pair": pair,
        "rate": float(rate),
        "source": "mock",
        "last_updated": MOCK_UPDATED_AT,
        "stale": False,
    }
