# Portfolio Notes

## Project Story

This project turns a workshop idea into a reproducible Data Engineering pipeline:

1. collect aviation wildlife strike records;
2. normalize raw records into staging tables;
3. attach airport reference data;
4. enrich event dates with weather;
5. validate coverage and mart grain;
6. export an analytical CSV for downstream DA/DS use.

## Current Evidence

- Offline end-to-end run with deterministic sample data.
- SQLite schema with raw, staging, dimension, weather, and mart layers.
- CLI commands for each pipeline step.
- Unit tests based on Python standard library.
- Data-quality checks for required event fields, weather uniqueness, weather coverage, and mart grain.
- Airflow-compatible DAG shell for future orchestration verification.

## Resume Bullet Draft

Built a reproducible Python and SQLite ETL pipeline that loads FAA-style wildlife strike records, joins airport reference data, enriches events with historical weather, validates data quality, and exports a daily analytical mart.

## Next Portfolio Proof Points

- Replace sample wildlife CSV with a documented FAA export.
- Add a Docker Compose runner.
- Add CI for unit tests and offline pipeline execution.
- Verify DAG import in an Airflow container.
- Add a small chart or dashboard artifact from the exported mart.
