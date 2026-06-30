from __future__ import annotations

import csv
from contextlib import closing
from pathlib import Path

from .db import connect


def load_airports_csv(db_path: str | Path, csv_path: str | Path) -> int:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    normalized = [_normalize_airport(row) for row in rows]
    with closing(connect(db_path)) as conn:
        with conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO dim_airport (
                    airport_code,
                    airport_name,
                    latitude,
                    longitude,
                    country
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["airport_code"],
                        row["airport_name"],
                        row["latitude"],
                        row["longitude"],
                        row["country"],
                    )
                    for row in normalized
                ],
            )
    return len(normalized)


def _to_float(value: str) -> float | None:
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None

def _normalize_airport(row: dict[str, str]) -> dict[str, object]:
    return {
        "airport_code": row["airport_code"].strip().upper(),
        "airport_name": row.get("airport_name", "").strip() or None,
        "latitude": _to_float(row.get("latitude", "")),
        "longitude": _to_float(row.get("longitude", "")),
        "country": row.get("country", "").strip().upper() or None,
    }
