from __future__ import annotations

import argparse
import sys
from contextlib import closing
from datetime import date

from .airports import load_airports_csv
from .db import connect, init_db
from .dq import format_results, run_checks
from .exports import export_daily_mart, format_summary, pipeline_summary
from .open_meteo import WeatherRequest, fetch_daily_weather
from .strikes import load_strikes_csv
from .weather import enrich_missing_weather, load_weather_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Bird strike weather pipeline helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Create SQLite schema")
    init_parser.add_argument("--db", required=True, help="SQLite database path")

    load_parser = subparsers.add_parser("load-strikes-csv", help="Load wildlife strike CSV into staging")
    load_parser.add_argument("--db", required=True, help="SQLite database path")
    load_parser.add_argument("--csv", required=True, help="CSV file path")

    airport_parser = subparsers.add_parser("load-airports", help="Load airport reference CSV")
    airport_parser.add_argument("--db", required=True, help="SQLite database path")
    airport_parser.add_argument("--csv", required=True, help="CSV file path")

    enrich_parser = subparsers.add_parser("enrich-weather", help="Fetch missing Open-Meteo weather rows")
    enrich_parser.add_argument("--db", required=True, help="SQLite database path")
    enrich_parser.add_argument("--limit", type=int, default=None, help="Maximum airport/date rows to fetch")

    weather_parser = subparsers.add_parser("load-weather-csv", help="Load daily weather CSV")
    weather_parser.add_argument("--db", required=True, help="SQLite database path")
    weather_parser.add_argument("--csv", required=True, help="CSV file path")

    export_parser = subparsers.add_parser("export-mart", help="Export daily strike-weather mart to CSV")
    export_parser.add_argument("--db", required=True, help="SQLite database path")
    export_parser.add_argument("--output", required=True, help="Output CSV path")

    summary_parser = subparsers.add_parser("summary", help="Print pipeline table counts and coverage")
    summary_parser.add_argument("--db", required=True, help="SQLite database path")

    dq_parser = subparsers.add_parser("dq", help="Run local data-quality checks")
    dq_parser.add_argument("--db", required=True, help="SQLite database path")

    sample_parser = subparsers.add_parser(
        "fetch-weather-sample",
        help="Fetch one Open-Meteo sample row for JFK on 2023-08-01",
    )
    sample_parser.add_argument("--db", required=True, help="SQLite database path")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db(args.db)
        print(f"Initialized database: {args.db}")
        return

    if args.command == "load-strikes-csv":
        init_db(args.db)
        row_count = load_strikes_csv(args.db, args.csv)
        print(f"Loaded strike rows: {row_count}")
        return

    if args.command == "load-airports":
        init_db(args.db)
        row_count = load_airports_csv(args.db, args.csv)
        print(f"Loaded airport rows: {row_count}")
        return

    if args.command == "enrich-weather":
        init_db(args.db)
        row_count = enrich_missing_weather(args.db, limit=args.limit)
        print(f"Inserted weather rows: {row_count}")
        return

    if args.command == "load-weather-csv":
        init_db(args.db)
        row_count = load_weather_csv(args.db, args.csv)
        print(f"Loaded weather rows: {row_count}")
        return

    if args.command == "export-mart":
        row_count = export_daily_mart(args.db, args.output)
        print(f"Exported mart rows: {row_count}")
        return

    if args.command == "summary":
        print(format_summary(pipeline_summary(args.db)))
        return

    if args.command == "dq":
        results = run_checks(args.db)
        print(format_results(results))
        if not all(result.passed for result in results):
            sys.exit(1)
        return

    if args.command == "fetch-weather-sample":
        init_db(args.db)
        request = WeatherRequest(
            airport_code="JFK",
            latitude=40.6413,
            longitude=-73.7781,
            start_date=date(2023, 8, 1),
            end_date=date(2023, 8, 1),
        )
        rows = list(fetch_daily_weather(request))
        if not rows:
            print("No weather data returned.")
            return
        row = rows[0]
        with closing(connect(args.db)) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO dim_airport
                        (airport_code, airport_name, latitude, longitude, country)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("JFK", "John F. Kennedy International Airport", 40.6413, -73.7781, "US"),
                )
                conn.execute(
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
                    (
                        row["airport_code"],
                        row["weather_date"],
                        row["temperature_2m_mean"],
                        row["precipitation_sum"],
                        row["wind_speed_10m_max"],
                        row["wind_gusts_10m_max"],
                        row["weather_code"],
                    ),
                )
        print(f"Inserted weather sample: {row}")


if __name__ == "__main__":
    main()
