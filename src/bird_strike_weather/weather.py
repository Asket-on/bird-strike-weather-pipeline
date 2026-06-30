from __future__ import annotations

import csv
from datetime import date
from contextlib import closing
from pathlib import Path

from .db import connect
from .open_meteo import WeatherRequest, fetch_daily_weather


def load_weather_csv(db_path: str | Path, csv_path: str | Path) -> int:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = [_normalize_weather(row) for row in csv.DictReader(file)]

    with closing(connect(db_path)) as conn:
        with conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO weather_daily (
                    airport_code,
                    weather_date,
                    temperature_2m_mean,
                    precipitation_sum,
                    wind_speed_10m_max,
                    wind_gusts_10m_max,
                    weather_code,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["airport_code"],
                        row["weather_date"],
                        row["temperature_2m_mean"],
                        row["precipitation_sum"],
                        row["wind_speed_10m_max"],
                        row["wind_gusts_10m_max"],
                        row["weather_code"],
                        row["source"],
                    )
                    for row in rows
                ],
            )
    return len(rows)


def enrich_missing_weather(db_path: str | Path, limit: int | None = None) -> int:
    requests = _missing_weather_requests(db_path, limit=limit)
    inserted = 0
    with closing(connect(db_path)) as conn:
        for request in requests:
            try:
                rows = list(fetch_daily_weather(request))
                with conn:
                    conn.executemany(
                        """
                        INSERT OR REPLACE INTO weather_daily (
                            airport_code,
                            weather_date,
                            temperature_2m_mean,
                            precipitation_sum,
                            wind_speed_10m_max,
                            wind_gusts_10m_max,
                            weather_code
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                row["airport_code"],
                                row["weather_date"],
                                row["temperature_2m_mean"],
                                row["precipitation_sum"],
                                row["wind_speed_10m_max"],
                                row["wind_gusts_10m_max"],
                                row["weather_code"],
                            )
                            for row in rows
                        ],
                    )
                inserted += len(rows)
            except Exception as e:
                print(f"Failed to fetch weather for {request.airport_code}: {e}")
    return inserted


def _missing_weather_requests(db_path: str | Path, limit: int | None = None) -> list[WeatherRequest]:
    query = """
        SELECT
            s.airport_code,
            MIN(s.incident_date) AS min_date,
            MAX(s.incident_date) AS max_date,
            a.latitude,
            a.longitude
        FROM staging_strikes AS s
        JOIN dim_airport AS a
            ON s.airport_code = a.airport_code
        LEFT JOIN weather_daily AS w
            ON s.airport_code = w.airport_code
           AND s.incident_date = w.weather_date
        WHERE s.incident_date IS NOT NULL
          AND a.latitude IS NOT NULL
          AND a.longitude IS NOT NULL
          AND w.airport_code IS NULL
        GROUP BY s.airport_code, a.latitude, a.longitude
        ORDER BY s.airport_code
    """
    if limit is not None:
        query += " LIMIT ?"
        params: tuple[int, ...] = (limit,)
    else:
        params = ()

    with closing(connect(db_path)) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        WeatherRequest(
            airport_code=row["airport_code"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            start_date=date.fromisoformat(row["min_date"]),
            end_date=date.fromisoformat(row["max_date"]),
        )
        for row in rows
    ]


def _normalize_weather(row: dict[str, str]) -> dict[str, object]:
    return {
        "airport_code": row["airport_code"].strip().upper(),
        "weather_date": row["weather_date"].strip(),
        "temperature_2m_mean": _to_float(row.get("temperature_2m_mean")),
        "precipitation_sum": _to_float(row.get("precipitation_sum")),
        "wind_speed_10m_max": _to_float(row.get("wind_speed_10m_max")),
        "wind_gusts_10m_max": _to_float(row.get("wind_gusts_10m_max")),
        "weather_code": _to_int(row.get("weather_code")),
        "source": row.get("source", "").strip() or "sample",
    }


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _to_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(float(str(value)))
