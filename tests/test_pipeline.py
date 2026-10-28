from __future__ import annotations

import tempfile
import unittest
import sqlite3
from contextlib import closing
from pathlib import Path

from bird_strike_weather.airports import load_airports_csv
from bird_strike_weather.db import init_db
from bird_strike_weather.dq import run_checks
from bird_strike_weather.exports import export_daily_mart, pipeline_summary
from bird_strike_weather.open_meteo import WeatherRequest, build_daily_weather_url
from bird_strike_weather.strikes import load_strikes_csv
from bird_strike_weather.weather import _missing_weather_requests, load_weather_csv
from datetime import date


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PipelineTest(unittest.TestCase):
    def test_sample_load_and_dq(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite"
            init_db(db_path)

            strike_count = load_strikes_csv(db_path, PROJECT_ROOT / "data/raw/sample_wildlife_strikes.csv")
            airport_count = load_airports_csv(db_path, PROJECT_ROOT / "data/raw/sample_airports.csv")
            weather_count = load_weather_csv(db_path, PROJECT_ROOT / "data/raw/sample_weather_daily.csv")
            results = run_checks(db_path)

            self.assertEqual(strike_count, 3)
            self.assertEqual(airport_count, 2)
            self.assertEqual(weather_count, 2)
            self.assertTrue(all(result.passed for result in results))

            with closing(sqlite3.connect(db_path)) as conn:
                rows = conn.execute(
                    """
                    SELECT incident_date, airport_code, strike_count, temperature_2m_mean
                    FROM mart_daily_strike_weather
                    ORDER BY incident_date, airport_code
                    """
                ).fetchall()

            self.assertEqual(rows, [("2023-08-01", "JFK", 2, 25.4), ("2023-08-02", "LGA", 1, 24.8)])

            summary = pipeline_summary(db_path)
            self.assertEqual(summary["staging_strikes"], 3)
            self.assertEqual(summary["weather_coverage_ratio"], 1.0)

            output_path = Path(tmpdir) / "mart.csv"
            exported_count = export_daily_mart(db_path, output_path)
            self.assertEqual(exported_count, 2)
            self.assertIn("incident_date,airport_code,strike_count", output_path.read_text(encoding="utf-8"))

    def test_missing_weather_requests_use_airport_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite"
            init_db(db_path)
            load_strikes_csv(db_path, PROJECT_ROOT / "data/raw/sample_wildlife_strikes.csv")
            load_airports_csv(db_path, PROJECT_ROOT / "data/raw/sample_airports.csv")

            requests = _missing_weather_requests(db_path)

            self.assertEqual(
                [(request.airport_code, request.start_date.isoformat(), request.end_date.isoformat()) for request in requests],
                [("JFK", "2023-08-01", "2023-08-01"), ("LGA", "2023-08-02", "2023-08-02")],
            )

            load_weather_csv(db_path, PROJECT_ROOT / "data/raw/sample_weather_daily.csv")
            self.assertEqual(_missing_weather_requests(db_path), [])

    def test_faa_style_export_headers_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite"
            init_db(db_path)
            row_count = load_strikes_csv(db_path, PROJECT_ROOT / "data/raw/sample_faa_style_export.csv")

            self.assertEqual(row_count, 2)
            with closing(sqlite3.connect(db_path)) as conn:
                rows = conn.execute(
                    """
                    SELECT strike_id, incident_date, airport_code, aircraft_type, species_name
                    FROM staging_strikes
                    ORDER BY strike_id
                    """
                ).fetchall()

            self.assertEqual(
                rows,
                [
                    ("FAA-SAMPLE-001", "2023-08-01", "JFK", "B-737", "CANADA GOOSE"),
                    ("FAA-SAMPLE-002", "2023-08-02", "LGA", "E-175", "UNKNOWN BIRD"),
                ],
            )

    def test_open_meteo_url_contains_expected_parameters(self) -> None:
        url = build_daily_weather_url(
            WeatherRequest(
                airport_code="JFK",
                latitude=40.6413,
                longitude=-73.7781,
                start_date=date(2023, 8, 1),
                end_date=date(2023, 8, 1),
            )
        )

        self.assertIn("latitude=40.6413", url)
        self.assertIn("longitude=-73.7781", url)
        self.assertIn("start_date=2023-08-01", url)
        self.assertIn("temperature_2m_mean", url)

    def test_open_meteo_batch_url_contains_multiple_coordinates(self) -> None:
        from bird_strike_weather.open_meteo import build_daily_weather_batch_url
        req1 = WeatherRequest(
            airport_code="JFK",
            latitude=40.6413,
            longitude=-73.7781,
            start_date=date(2023, 8, 1),
            end_date=date(2023, 8, 1),
        )
        req2 = WeatherRequest(
            airport_code="LGA",
            latitude=40.7772,
            longitude=-73.8726,
            start_date=date(2023, 8, 1),
            end_date=date(2023, 8, 1),
        )
        url = build_daily_weather_batch_url([req1, req2])
        self.assertIn("latitude=40.6413%2C40.7772", url)
        self.assertIn("longitude=-73.7781%2C-73.8726", url)
        self.assertIn("start_date=2023-08-01", url)

    def test_enrich_missing_weather_raises_on_complete_failure(self) -> None:
        from unittest.mock import patch
        from bird_strike_weather.weather import enrich_missing_weather

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.sqlite"
            init_db(db_path)
            load_strikes_csv(db_path, PROJECT_ROOT / "data/raw/sample_wildlife_strikes.csv")
            load_airports_csv(db_path, PROJECT_ROOT / "data/raw/sample_airports.csv")

            with patch("bird_strike_weather.weather.fetch_daily_weather_batch", side_effect=Exception("API connection timeout")):
                with self.assertRaises(RuntimeError) as ctx:
                    enrich_missing_weather(db_path)
                self.assertIn("Weather enrichment failed completely", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
