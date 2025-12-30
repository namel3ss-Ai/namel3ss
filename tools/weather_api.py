from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from namel3ss_safeio import safe_env_get, safe_open, safe_urlopen

from examples.demos._shared import api_cache, api_resilience


PRIMARY_ENV = "WEATHER_API_KEY"
SECONDARY_ENV = "WEATHER_API_SECONDARY_KEY"
FORCE_FAIL_ENV = "WEATHER_API_FORCE_FAIL"

PRIMARY_URL = "https://api.weatherapi.com/v1/forecast.json"
SECONDARY_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
SECONDARY_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CACHE_TTL_SECONDS = 30 * 60
TIMEOUT_SECONDS = 8
RETRY_POLICY = api_resilience.RetryPolicy(max_attempts=3, base_delay=0.2, max_delay=1.0)
CIRCUIT_FAILURE_THRESHOLD = 2
CIRCUIT_OPEN_SECONDS = 60

FIXTURE_PATH = Path("examples/demos/weather_dashboard/fixtures/weather_brussels.json")
MOCK_UPDATED_AT = "2024-01-01T00:00:00Z"
MOCK_DAYS = [
    {"date": "2024-05-01", "condition": "Sunny", "temperature": 27},
    {"date": "2024-05-02", "condition": "Partly cloudy", "temperature": 24},
    {"date": "2024-05-03", "condition": "Light rain", "temperature": 22},
]

WEATHER_CODE_MAP = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    95: "Thunderstorm",
}


def run(payload: dict[str, Any]) -> dict[str, Any]:
    city = _normalize_city(payload.get("city"))
    primary_key = safe_env_get(PRIMARY_ENV)
    secondary_key = safe_env_get(SECONDARY_ENV)
    if not (primary_key or secondary_key):
        return _mock_response()
    now = api_cache.now_timestamp()
    cache_key = f"weather:{city.lower()}"
    providers = [
        ("primary", primary_key, lambda: _fetch_primary(city, primary_key)),
        ("secondary", secondary_key, lambda: _fetch_secondary(city)),
    ]
    for name, token, fetcher in providers:
        if not token:
            continue
        days = _attempt_provider(name, fetcher, now)
        if days is None:
            continue
        entry = api_cache.set_response(cache_key, {"days": days}, updated_ts=now)
        return {
            "days": days,
            "source": "api",
            "note": f"Live data from {name} provider.",
            "last_updated": entry.updated_at,
            "stale": False,
        }

    cached = api_cache.get_response(cache_key)
    if cached:
        cached_days = _payload_days(cached.payload)
        if cached_days:
            stale = not api_cache.is_fresh(cached, CACHE_TTL_SECONDS, now=now)
            return {
                "days": cached_days,
                "source": "cache",
                "note": "Using cached data.",
                "last_updated": cached.updated_at,
                "stale": stale,
            }

    fixture = _load_fixture(city)
    if fixture is not None:
        return {
            "days": fixture["days"],
            "source": "fixture",
            "note": "Using fixture data.",
            "last_updated": fixture["last_updated"],
            "stale": False,
        }

    return _mock_response()


def _normalize_city(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Brussels"


def _attempt_provider(name: str, fetcher, now: float) -> list[dict[str, Any]] | None:
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
        days = api_resilience.call_with_retries(fetcher, RETRY_POLICY)
    except Exception:
        api_cache.record_failure(
            _circuit_key(name),
            now=now,
            threshold=CIRCUIT_FAILURE_THRESHOLD,
            open_seconds=CIRCUIT_OPEN_SECONDS,
        )
        return None
    api_cache.record_success(_circuit_key(name))
    return days


def _circuit_key(provider: str) -> str:
    return f"weather:{provider}"


def _force_fail() -> bool:
    value = safe_env_get(FORCE_FAIL_ENV)
    return isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}


def _fetch_primary(city: str, api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        raise ValueError("Missing primary API key")
    params = {
        "key": api_key,
        "q": city,
        "days": 3,
        "aqi": "no",
        "alerts": "no",
    }
    url = f"{PRIMARY_URL}?{parse.urlencode(params)}"
    data = _read_json(url)
    return _parse_weatherapi_days(data)


def _fetch_secondary(city: str) -> list[dict[str, Any]]:
    params = {"name": city, "count": 1}
    geo_url = f"{SECONDARY_GEO_URL}?{parse.urlencode(params)}"
    geo = _read_json(geo_url)
    lat, lon = _extract_geo(geo)
    if lat is None or lon is None:
        raise ValueError("Secondary geocoding returned no coordinates")
    forecast_params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,weathercode",
        "timezone": "UTC",
    }
    forecast_url = f"{SECONDARY_FORECAST_URL}?{parse.urlencode(forecast_params)}"
    forecast = _read_json(forecast_url)
    return _parse_open_meteo_days(forecast)


def _extract_geo(data: Any) -> tuple[float | None, float | None]:
    if not isinstance(data, dict):
        return None, None
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None, None
    first = results[0]
    if not isinstance(first, dict):
        return None, None
    lat = first.get("latitude")
    lon = first.get("longitude")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon)
    return None, None


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


def _parse_weatherapi_days(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise ValueError("Weather API returned invalid payload")
    forecast = data.get("forecast")
    if not isinstance(forecast, dict):
        raise ValueError("Weather API missing forecast data")
    days = forecast.get("forecastday")
    if not isinstance(days, list):
        raise ValueError("Weather API missing forecast days")
    output: list[dict[str, Any]] = []
    for item in days:
        if not isinstance(item, dict):
            continue
        date = item.get("date")
        day = item.get("day")
        if not isinstance(day, dict):
            continue
        condition = day.get("condition")
        summary = None
        if isinstance(condition, dict):
            summary = condition.get("text")
        temp = day.get("avgtemp_c")
        if date is None or summary is None or temp is None:
            continue
        output.append(
            {
                "date": str(date),
                "condition": str(summary),
                "temperature": float(temp),
            }
        )
    if not output:
        raise ValueError("Weather API returned no usable forecast")
    return output


def _parse_open_meteo_days(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise ValueError("Open-Meteo returned invalid payload")
    daily = data.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Open-Meteo missing daily data")
    dates = daily.get("time")
    temps = daily.get("temperature_2m_max")
    codes = daily.get("weathercode")
    if not isinstance(dates, list) or not isinstance(temps, list) or not isinstance(codes, list):
        raise ValueError("Open-Meteo missing arrays")
    output: list[dict[str, Any]] = []
    for date, temp, code in zip(dates, temps, codes):
        if len(output) >= 3:
            break
        if date is None or temp is None or code is None:
            continue
        summary = WEATHER_CODE_MAP.get(int(code), "Unknown")
        output.append(
            {
                "date": str(date),
                "condition": summary,
                "temperature": float(temp),
            }
        )
    if not output:
        raise ValueError("Open-Meteo returned no usable forecast")
    return output


def _payload_days(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        days = payload.get("days")
        if isinstance(days, list):
            return [item for item in days if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _load_fixture(city: str) -> dict[str, Any] | None:
    if city.strip().lower() != "brussels":
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
    days = data.get("days")
    last_updated = data.get("last_updated")
    if not isinstance(days, list) or not isinstance(last_updated, str):
        return None
    return {"days": days, "last_updated": last_updated}


def _mock_response() -> dict[str, Any]:
    days = [dict(day) for day in MOCK_DAYS]
    return {
        "days": days,
        "source": "mock",
        "note": "Using mock data.",
        "last_updated": MOCK_UPDATED_AT,
        "stale": False,
    }
