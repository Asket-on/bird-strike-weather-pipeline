from __future__ import annotations

import csv
from contextlib import closing
from pathlib import Path

from .db import connect


MART_QUERY = """
SELECT
    incident_date,
    airport_code,
    strike_count,
    strikes_with_damage_level,
    temperature_2m_mean,
    precipitation_sum,
    wind_speed_10m_max,
    wind_gusts_10m_max
FROM mart_daily_strike_weather
ORDER BY incident_date, airport_code
"""


def export_daily_mart(db_path: str | Path, output_path: str | Path) -> int:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect(db_path)) as conn:
        rows = conn.execute(MART_QUERY).fetchall()

    fieldnames = [
        "incident_date",
        "airport_code",
        "strike_count",
        "strikes_with_damage_level",
        "temperature_2m_mean",
        "precipitation_sum",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
    ]
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fieldnames})
    return len(rows)


def pipeline_summary(db_path: str | Path) -> dict[str, int | float]:
    with closing(connect(db_path)) as conn:
        strike_count = _scalar(conn, "SELECT COUNT(*) FROM staging_strikes")
        airport_count = _scalar(conn, "SELECT COUNT(*) FROM dim_airport")
        weather_count = _scalar(conn, "SELECT COUNT(*) FROM weather_daily")
        mart_count = _scalar(conn, "SELECT COUNT(*) FROM mart_daily_strike_weather")
        missing_weather = _scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM staging_strikes AS s
            LEFT JOIN weather_daily AS w
                ON s.airport_code = w.airport_code
               AND s.incident_date = w.weather_date
            WHERE w.airport_code IS NULL
            """,
        )

    weather_coverage = 1.0 if strike_count == 0 else (strike_count - missing_weather) / strike_count
    return {
        "staging_strikes": strike_count,
        "dim_airport": airport_count,
        "weather_daily": weather_count,
        "mart_daily_strike_weather": mart_count,
        "missing_weather_matches": missing_weather,
        "weather_coverage_ratio": round(weather_coverage, 4),
    }


def format_summary(summary: dict[str, int | float]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in summary.items())


def _scalar(conn, query: str) -> int:
    return conn.execute(query).fetchone()[0]
