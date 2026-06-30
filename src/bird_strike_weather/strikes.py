from __future__ import annotations

import csv
import hashlib
import json
import re
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .db import connect


FIELD_ALIASES = {
    "strike_id": ["strike_id", "incident_id", "index_nr", "record_id"],
    "incident_date": ["incident_date", "date", "incident_date_only", "incident_dt"],
    "airport_code": ["airport_code", "airport_id", "iata", "faa_airport"],
    "airport_name": ["airport_name", "airport"],
    "aircraft_type": ["aircraft_type", "aircraft", "atype"],
    "operator_name": ["operator_name", "operator", "airline"],
    "species_name": ["species_name", "species", "wildlife_species"],
    "flight_phase": ["flight_phase", "phase_of_flight", "phase"],
    "height_ft": ["height_ft", "height", "altitude_ft"],
    "damage_level": ["damage_level", "damage", "damage_code"],
}


def load_strikes_csv(db_path: str | Path, csv_path: str | Path) -> int:
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = [_normalize_row(row) for row in reader]

    with closing(connect(db_path)) as conn:
        with conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO raw_strike_files (file_name, source_url)
                VALUES (?, ?)
                """,
                (path.name, str(path)),
            )
            conn.executemany(
                """
                INSERT OR REPLACE INTO staging_strikes (
                    strike_id,
                    file_name,
                    incident_date,
                    airport_code,
                    airport_name,
                    aircraft_type,
                    operator_name,
                    species_name,
                    flight_phase,
                    height_ft,
                    damage_level,
                    raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["strike_id"],
                        path.name,
                        row["incident_date"],
                        row["airport_code"],
                        row["airport_name"],
                        row["aircraft_type"],
                        row["operator_name"],
                        row["species_name"],
                        row["flight_phase"],
                        row["height_ft"],
                        row["damage_level"],
                        row["raw_payload"],
                    )
                    for row in rows
                ],
            )
    return len(rows)


def _normalize_row(row: dict[str, str]) -> dict[str, object]:
    normalized_keys = {_clean_key(key): value for key, value in row.items()}
    output: dict[str, object] = {}
    for target, aliases in FIELD_ALIASES.items():
        output[target] = _first_value(normalized_keys, aliases)

    if not output["strike_id"]:
        output["strike_id"] = _stable_id(row)

    output["incident_date"] = _normalize_date(output["incident_date"])
    output["airport_code"] = _clean_code(output["airport_code"])
    output["height_ft"] = _to_int(output["height_ft"])
    output["raw_payload"] = json.dumps(row, ensure_ascii=True, sort_keys=True)
    return output


def _first_value(row: dict[str, str], aliases: Iterable[str]) -> str | None:
    for alias in aliases:
        value = row.get(_clean_key(alias))
        if value is not None and value.strip() != "":
            return value.strip()
    return None


def _clean_key(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def _clean_code(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().upper() or None


def _to_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def _normalize_date(value: object) -> str | None:
    if not isinstance(value, str) or value.strip() == "":
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _stable_id(row: dict[str, str]) -> str:
    payload = json.dumps(row, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
