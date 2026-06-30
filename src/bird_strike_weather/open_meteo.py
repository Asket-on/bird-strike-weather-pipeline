from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Iterator
from urllib.parse import urlencode
from urllib.request import urlopen


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


@dataclass(frozen=True)
class WeatherRequest:
    airport_code: str
    latitude: float
    longitude: float
    start_date: date
    end_date: date


def build_daily_weather_url(request: WeatherRequest) -> str:
    params = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_mean",
                "precipitation_sum",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
            ]
        ),
        "timezone": "UTC",
    }
    return f"{ARCHIVE_URL}?{urlencode(params)}"


def fetch_daily_weather(request: WeatherRequest) -> Iterator[dict[str, object]]:
    url = build_daily_weather_url(request)
    
    max_retries = 3
    payload = {}
    for attempt in range(max_retries):
        try:
            with urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    daily = payload.get("daily", {})
    times = daily.get("time", [])
    
    for i, w_date in enumerate(times):
        yield {
            "airport_code": request.airport_code,
            "weather_date": w_date,
            "temperature_2m_mean": _safe_get(daily.get("temperature_2m_mean"), i),
            "precipitation_sum": _safe_get(daily.get("precipitation_sum"), i),
            "wind_speed_10m_max": _safe_get(daily.get("wind_speed_10m_max"), i),
            "wind_gusts_10m_max": _safe_get(daily.get("wind_gusts_10m_max"), i),
            "weather_code": _safe_get(daily.get("weather_code"), i),
        }


def _safe_get(values: object, index: int) -> object:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None
