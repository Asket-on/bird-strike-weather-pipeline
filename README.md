# Bird Strike Weather Pipeline
[![CI](https://github.com/Asket-on/bird-strike-weather-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Asket-on/bird-strike-weather-pipeline/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Asket-on/bird-strike-weather-pipeline/blob/main/LICENSE)

An automated, reproducible Data Engineering pipeline that ingests aviation wildlife strike records and enriches them with historical daily weather observations to evaluate the meteorological impact on aircraft bird strikes.

---

## Key Architectural Highlights

* **Zero-Dependency Core Architecture:** Built strictly with the Python 3.10+ Standard Library (`sqlite3`, `urllib`, `csv`, `hashlib`, `dataclasses`, `unittest`, `logging`). Guarantees 100% deterministic builds, zero supply-chain vulnerabilities, and instant cold-start execution in any CI/CD or containerized environment without external wheel installations.
* **Schema-on-Write with Raw Audit Fallback:** The ingestion engine (`strikes.py`) maps diverse raw FAA schemas via dynamic field aliasing while preserving the complete, immutable raw record in `raw_payload` (JSON) alongside deterministic SHA-256 surrogate keys (`_stable_id`). If downstream requirements evolve, historical data can be re-indexed without re-downloading source files.
* **Write-Audit-Publish (WAP) Quality Gates:** Orchestrated tasks enforce strict gatekeeping (`weather >> dq >> mart`). Data Quality assertions (`dq.py`) act as an automated circuit breaker verifying non-null constraints, 100% weather coverage, and strict grain uniqueness (`incident_date + airport_code`). Corrupted or partial batches are blocked before publication to the analytical mart.
* **Resilient Multi-Coordinate API Batching:** Queries the Open-Meteo Historical Weather API with multi-coordinate batching (chunk size = 50 locations) and exponential backoff, avoiding URL length limits and eliminating N+1 API bottlenecks.

---

## Pipeline Architecture

```
[FAA Wildlife CSVs] ---> [Staging Layer: SQLite] ---> [Open-Meteo Batch API]
                                |                              |
                                v                              v
                      [raw_strike_files]               [weather_daily]
                      [staging_strikes ]                       |
                                \                             /
                                 v                           v
                           [Write-Audit-Publish: dq.py Checks]
                                         |
                                         v (Pass Gate)
                           [mart_daily_strike_weather.csv]
```

1. **Ingestion & Lineage:** Raw FAA strike CSVs and reference airport data are parsed into `staging_strikes` and `dim_airport` with file-level lineage tracking in `raw_strike_files`.
2. **Weather Enrichment:** Spatial weather service batches missing date/airport combinations and retrieves daily observations with retry resilience.
3. **Data Quality Circuit Breaker:** Automated tests validate schema contracts, primary keys, and data completeness.
4. **Data Mart Publication:** A clean analytical view (`mart_daily_strike_weather`) aggregates daily strike frequencies and joins daily meteorological metrics for downstream analytics.
5. **Orchestration:** Packaged with an Apache Airflow DAG (`dags/bird_strike_weather_dag.py`) and a standalone Docker Compose runner.

---

## Quick Start

### Prerequisites
* Python **3.10+** (utilizes PEP 604 union syntax `str | Path` and standard library modules).
* Git.

### 1. Local CLI Execution

**macOS / Linux (Bash / Zsh):**
```bash
export PYTHONPATH=src
DB="data/processed/bird_strikes.sqlite"

# 1. Initialize SQLite Database Schema
python3 -m bird_strike_weather.cli init-db --db "$DB"

# 2. Ingest Reference Airports and Wildlife Strike Data
python3 -m bird_strike_weather.cli load-airports --db "$DB" --csv data/raw/sample_airports.csv
python3 -m bird_strike_weather.cli load-strikes-csv --db "$DB" --csv data/raw/sample_wildlife_strikes.csv

# 3. Enrich Weather via Open-Meteo Batch API
python3 -m bird_strike_weather.cli enrich-weather --db "$DB"

# 4. Execute Write-Audit-Publish Data Quality Checks
python3 -m bird_strike_weather.cli dq --db "$DB"
python3 -m bird_strike_weather.cli summary --db "$DB"

# 5. Export Published Analytical Mart
python3 -m bird_strike_weather.cli export-mart --db "$DB" --output data/processed/mart_daily_strike_weather.csv
```

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="src"
$db="data/processed/bird_strikes.sqlite"

python -m bird_strike_weather.cli init-db --db $db
python -m bird_strike_weather.cli load-airports --db $db --csv data/raw/sample_airports.csv
python -m bird_strike_weather.cli load-strikes-csv --db $db --csv data/raw/sample_wildlife_strikes.csv
python -m bird_strike_weather.cli enrich-weather --db $db
python -m bird_strike_weather.cli dq --db $db
python -m bird_strike_weather.cli summary --db $db
python -m bird_strike_weather.cli export-mart --db $db --output data/processed/mart_daily_strike_weather.csv
```

Alternatively, run the sample pipeline via `make`:
```bash
make sample
```

### 2. Docker & Airflow Orchestration

Run the complete pipeline within isolated containers:

```bash
# Start Airflow Standalone and Test-Runner
docker compose up -d

# Inspect DAG status in Airflow UI
# Available at: http://localhost:8080
```

---

## Running Tests & CI/CD

Unit tests validate API URL generation, multi-coordinate batching, date-range calculations, and resilient schema parsing:

```bash
# macOS / Linux:
PYTHONPATH=src python3 -m unittest discover -s tests -v

# Windows (PowerShell):
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

GitHub Actions automatically runs the test suite and an end-to-end integration run across Python **3.10, 3.11, and 3.12** on every commit.

---

## Tech Stack & Tooling

| Component | Technology | Rationale |
|---|---|---|
| **Language & Core** | Python 3.10+ (Standard Library) | Zero supply-chain risk, zero external dependencies, deterministic execution. |
| **Relational Storage** | SQLite3 (ANSI SQL compliant) | Lightweight, serverless local portability; seamless migration path to PostgreSQL/DuckDB. |
| **Orchestration** | Apache Airflow 2.7.2 (`@dag`, `@task`) | Production-ready task graph with task isolation and dependency management. |
| **Data Quality** | Custom Circuit Breaker (`dq.py`) | Write-Audit-Publish pattern with strict grain and completeness assertions. |
| **Containers & CI** | Docker Compose / GitHub Actions | Reproducible multi-version execution across Ubuntu runners. |

---

## Design Trade-offs & Known Limitations

* **Date-Range Batching:** Current weather requests are grouped by `(min_date, max_date)` per airport. For multi-decade historical FAA datasets with sparse occurrences, partitioning requests into monthly or yearly intervals will further optimize API payload efficiency.
* **Storage Engine:** SQLite is selected for zero-friction local and CI portability. The DDL and SQL queries adhere strictly to ANSI SQL for effortless migration to PostgreSQL, Snowflake, or DuckDB.
