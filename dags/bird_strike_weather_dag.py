from __future__ import annotations

from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "bird_strikes.sqlite"


def init_database() -> None:
    from bird_strike_weather.db import init_db

    init_db(DB_PATH)


try:
    from airflow.decorators import dag, task
except ImportError:
    dag = None
    task = None


if dag and task:

    @dag(
        dag_id="bird_strike_weather_pipeline",
        start_date=datetime(2026, 1, 1),
        schedule="@daily",
        catchup=False,
        tags=["portfolio", "de", "weather"],
    )
    def bird_strike_weather_pipeline():
        @task
        def create_schema():
            init_database()

        @task
        def load_airports():
            from bird_strike_weather.airports import load_airports_csv
            load_airports_csv(DB_PATH, PROJECT_ROOT / "data" / "raw" / "sample_airports.csv")

        @task
        def load_strikes():
            from bird_strike_weather.strikes import load_strikes_csv
            load_strikes_csv(DB_PATH, PROJECT_ROOT / "data" / "raw" / "sample_wildlife_strikes.csv")

        @task
        def enrich_weather():
            from bird_strike_weather.weather import enrich_missing_weather
            enrich_missing_weather(DB_PATH)

        @task
        def run_dq():
            from bird_strike_weather.dq import run_checks
            results = run_checks(DB_PATH)
            for r in results:
                if not r.passed:
                    raise ValueError(f"DQ failed: {r.description}")

        @task
        def export_mart():
            from bird_strike_weather.exports import export_daily_mart
            export_daily_mart(DB_PATH, PROJECT_ROOT / "data" / "processed" / "mart.csv")

        schema = create_schema()
        airports = load_airports()
        strikes = load_strikes()
        weather = enrich_weather()
        dq = run_dq()
        mart = export_mart()

        schema >> [airports, strikes] >> weather >> dq >> mart

    bird_strike_weather_pipeline()
