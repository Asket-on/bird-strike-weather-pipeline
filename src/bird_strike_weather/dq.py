from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
from pathlib import Path

from .db import connect


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    observed_value: int | float
    details: str


def run_checks(db_path: str | Path) -> list[CheckResult]:
    with closing(connect(db_path)) as conn:
        staging_count = _scalar(conn, "SELECT COUNT(*) FROM staging_strikes")
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
        checks = [
            CheckResult(
                name="staging_has_rows",
                passed=staging_count > 0,
                observed_value=staging_count,
                details="staging_strikes must not be empty",
            ),
            CheckResult(
                name="incident_date_not_null",
                passed=_scalar(conn, "SELECT COUNT(*) FROM staging_strikes WHERE incident_date IS NULL") == 0,
                observed_value=_scalar(conn, "SELECT COUNT(*) FROM staging_strikes WHERE incident_date IS NULL"),
                details="all staged strikes need incident_date",
            ),
            CheckResult(
                name="airport_code_not_null",
                passed=_scalar(conn, "SELECT COUNT(*) FROM staging_strikes WHERE airport_code IS NULL") == 0,
                observed_value=_scalar(conn, "SELECT COUNT(*) FROM staging_strikes WHERE airport_code IS NULL"),
                details="weather enrichment requires airport_code",
            ),
            CheckResult(
                name="weather_daily_unique_grain",
                passed=_scalar(
                    conn,
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT airport_code, weather_date
                        FROM weather_daily
                        GROUP BY airport_code, weather_date
                        HAVING COUNT(*) > 1
                    )
                    """,
                )
                == 0,
                observed_value=_scalar(
                    conn,
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT airport_code, weather_date
                        FROM weather_daily
                        GROUP BY airport_code, weather_date
                        HAVING COUNT(*) > 1
                    )
                    """,
                ),
                details="weather_daily grain must be airport_code + weather_date",
            ),
            CheckResult(
                name="weather_coverage_complete",
                passed=staging_count == 0 or missing_weather == 0,
                observed_value=missing_weather,
                details="all staged strikes should have matching airport/date weather for full offline mart",
            ),
            CheckResult(
                name="mart_daily_unique_grain",
                passed=_scalar(
                    conn,
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT incident_date, airport_code
                        FROM mart_daily_strike_weather
                        GROUP BY incident_date, airport_code
                        HAVING COUNT(*) > 1
                    )
                    """,
                )
                == 0,
                observed_value=_scalar(
                    conn,
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT incident_date, airport_code
                        FROM mart_daily_strike_weather
                        GROUP BY incident_date, airport_code
                        HAVING COUNT(*) > 1
                    )
                    """,
                ),
                details="mart_daily_strike_weather grain must be incident_date + airport_code",
            ),
        ]
    return checks


def format_results(results: list[CheckResult]) -> str:
    lines = []
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"{status} {result.name}: {result.observed_value} ({result.details})")
    return "\n".join(lines)


def _scalar(conn, query: str) -> int:
    return conn.execute(query).fetchone()[0]
