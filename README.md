---
updated: 2026-06-30T19:32:24+02:00
---
# Bird Strike Weather Pipeline

An automated Data Engineering pipeline that ingests aviation wildlife strike records and enriches them with historical daily weather data to support analysis on how weather conditions affect aircraft bird strikes.

## Architecture

1. **Ingestion**: Raw FAA wildlife strike CSVs and reference airports are safely parsed into a SQLite staging layer (`staging_strikes` and `dim_airport`), with robust error handling for malformed data and data lineage tracking.
2. **Weather Enrichment**: A Python service queries the Open-Meteo API to fetch historical weather data for each incident. Requests are intelligently batched by date range (solving the N+1 API problem) and include exponential backoff for network resilience.
3. **Data Quality**: Assertions run across the staging and enriched tables to ensure 100% weather coverage, non-null constraints, and unique grain validation.
4. **Data Mart**: A final view (`mart_daily_strike_weather`) joins incidents with weather conditions, which is then exported as a CSV for downstream BI/Analytics.
5. **Orchestration**: Built with Python decorators ready to drop into an Apache Airflow DAG (`dags/bird_strike_weather_dag.py`).

## Quick Start (Local Demo)

The project requires Python 3.9+ and has zero external dependencies (uses standard library).

```powershell
# Set PYTHONPATH to the src directory
$env:PYTHONPATH="src"
$db="data/processed/bird_strikes.sqlite"

# 1. Initialize Database
python -m bird_strike_weather.cli init-db --db $db

# 2. Load Reference & Sample Data
python -m bird_strike_weather.cli load-airports --db $db --csv data/raw/sample_airports.csv
python -m bird_strike_weather.cli load-strikes-csv --db $db --csv data/raw/sample_wildlife_strikes.csv

# 3. Enrich Weather via Open-Meteo API
python -m bird_strike_weather.cli enrich-weather --db $db

# 4. Run Data Quality Checks
python -m bird_strike_weather.cli dq --db $db
python -m bird_strike_weather.cli summary --db $db

# 5. Export Mart
python -m bird_strike_weather.cli export-mart --db $db --output data/processed/mart_daily_strike_weather.csv
```

## Running Tests

Unit tests validate API URL construction, missing date range calculations, and CSV parsing behavior.

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests
```

## Tools & Tech Stack
- **Python**: Core pipeline logic, API integration, and CLI.
- **SQLite**: Local relational database for staging and analytical tables.
- **Airflow**: Orchestration structure (`@dag` and `@task`).
- **Open-Meteo API**: Historical weather data source.

## Known Limitations & Next Steps
- The pipeline currently uses SQLite for local portfolio demonstration. It can be easily migrated to PostgreSQL.
- Currently, the FAA dataset requires manual download. A future step is to automate raw file ingestion via an automated scraper if made available.
