from __future__ import annotations

import csv
import logging
from datetime import date
from contextlib import closing
from pathlib import Path

from .db import connect
from .open_meteo import WeatherRequest, fetch_daily_weather, fetch_daily_weather_batch

logger = logging.getLogger(__name__)


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
    if not requests:
        logger.info("No missing weather requests found.")
        return 0

    inserted = 0
    failed_batches: list[tuple[list[str], Exception]] = []

    # Group requests by (start_date, end_date)
    groups: dict[tuple[date, date], list[WeatherRequest]] = {}
    for req in requests:
        key = (req.start_date, req.end_date)
        groups.setdefault(key, []).append(req)

    with closing(connect(db_path)) as conn:
        for (start_date, end_date), group_reqs in groups.items():
            # Chunk group_reqs to max 50 requests per API call to prevent URL length limits
            chunk_size = 50
            for i in range(0, len(group_reqs), chunk_size):
                chunk = group_reqs[i : i + chunk_size]
                airport_codes = [r.airport_code for r in chunk]
                try:
                    rows = list(fetch_daily_weather_batch(chunk))
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
                    logger.error("Failed to fetch weather batch for airports %s: %s", airport_codes, e)
                    failed_batches.append((airport_codes, e))

    if failed_batches and inserted == 0:
        raise RuntimeError(
            f"Weather enrichment failed completely: {len(failed_batches)} batch(es) encountered errors."
        )
    elif failed_batches:
        logger.warning(
            "Weather enrichment completed with partial failures: %d batch(es) failed.",
            len(failed_batches),
        )

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

    requests = []
    for row in rows:
        try:
            start_date = date.fromisoformat(row["min_date"])
            end_date = date.fromisoformat(row["max_date"])
            requests.append(
                WeatherRequest(
                    airport_code=row["airport_code"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        except (ValueError, TypeError) as e:
            logger.warning(
                "Skipping weather request for %s due to invalid date formats (min_date=%s, max_date=%s): %s",
                row.get("airport_code"),
                row.get("min_date"),
                row.get("max_date"),
                e,
            )
    return requests


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
