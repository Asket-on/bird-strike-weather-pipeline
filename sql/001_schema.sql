CREATE TABLE IF NOT EXISTS raw_strike_files (
    file_id INTEGER PRIMARY KEY,
    file_name TEXT NOT NULL UNIQUE,
    source_url TEXT,
    loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staging_strikes (
    strike_id TEXT PRIMARY KEY,
    file_name TEXT,
    incident_date TEXT,
    airport_code TEXT,
    airport_name TEXT,
    aircraft_type TEXT,
    operator_name TEXT,
    species_name TEXT,
    flight_phase TEXT,
    height_ft INTEGER,
    damage_level TEXT,
    raw_payload TEXT,
    loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_strikes_airport_date ON staging_strikes(airport_code, incident_date);

CREATE TABLE IF NOT EXISTS dim_airport (
    airport_code TEXT PRIMARY KEY,
    airport_name TEXT,
    latitude REAL,
    longitude REAL,
    country TEXT
);

CREATE TABLE IF NOT EXISTS weather_daily (
    airport_code TEXT NOT NULL,
    weather_date TEXT NOT NULL,
    temperature_2m_mean REAL,
    precipitation_sum REAL,
    wind_speed_10m_max REAL,
    wind_gusts_10m_max REAL,
    weather_code INTEGER,
    source TEXT NOT NULL DEFAULT 'open-meteo',
    loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (airport_code, weather_date)
);

CREATE VIEW IF NOT EXISTS mart_daily_strike_weather AS
SELECT
    s.incident_date,
    s.airport_code,
    COUNT(*) AS strike_count,
    SUM(CASE WHEN s.damage_level IS NOT NULL AND s.damage_level <> '' THEN 1 ELSE 0 END) AS strikes_with_damage_level,
    w.temperature_2m_mean,
    w.precipitation_sum,
    w.wind_speed_10m_max,
    w.wind_gusts_10m_max
FROM staging_strikes AS s
LEFT JOIN weather_daily AS w
    ON s.airport_code = w.airport_code
   AND s.incident_date = w.weather_date
GROUP BY
    s.incident_date,
    s.airport_code,
    w.temperature_2m_mean,
    w.precipitation_sum,
    w.wind_speed_10m_max,
    w.wind_gusts_10m_max;
