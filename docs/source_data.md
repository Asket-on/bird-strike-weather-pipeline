# Source Data

## Primary Source

The target source is the FAA Wildlife Strike Database:

- Website: <https://wildlife.faa.gov/home>
- Search page: <https://wildlife.faa.gov/search>

The public site currently requires JavaScript for interactive use, so the first production ingestion path should support a manually exported file placed in `data/raw/`.

Older public reporting says the FAA database has been available through web forms and as a downloadable Microsoft Access database, but the current project should not rely on that older packaging without rechecking the live site.

## Access Contract

For the first real ingestion, use this contract:

1. Export or download wildlife strike records from the FAA site.
2. Save the file under `data/raw/`.
3. Keep the original file immutable.
4. Run `load-strikes-csv` against either:
   - a normalized CSV with project column names; or
   - an FAA-style CSV with uppercase source headers.

## Supported Strike Columns

The parser currently maps these source-style columns:

| Target field | Supported source headers |
|---|---|
| `strike_id` | `strike_id`, `incident_id`, `index_nr`, `record_id` |
| `incident_date` | `incident_date`, `date`, `incident_date_only` |
| `airport_code` | `airport_code`, `airport_id`, `iata`, `faa_airport` |
| `airport_name` | `airport_name`, `airport` |
| `aircraft_type` | `aircraft_type`, `aircraft`, `atype` |
| `operator_name` | `operator_name`, `operator`, `airline` |
| `species_name` | `species_name`, `species`, `wildlife_species` |
| `flight_phase` | `flight_phase`, `phase_of_flight`, `phase` |
| `height_ft` | `height_ft`, `height`, `altitude_ft` |
| `damage_level` | `damage_level`, `damage`, `damage_code` |

## Date Handling

Supported input date formats:

- `YYYY-MM-DD`
- `MM/DD/YYYY`
- `MM/DD/YY`

Dates are stored as `YYYY-MM-DD`.

## Known Source Risks

- The live FAA website is JavaScript-driven, so automated download may need browser automation rather than a simple HTTP request.
- Export column names may differ by format or site version.
- Wildlife strike reporting is not necessarily complete, so the dataset should not be used to claim true incident rates without a coverage caveat.
- Airport coordinates may require a separate reference dataset.
- The first public portfolio version should commit only small synthetic or sanitized samples, not a large raw FAA dump.

## Current Fixtures

- `data/raw/sample_wildlife_strikes.csv`: normalized project sample.
- `data/raw/sample_faa_style_export.csv`: FAA-style header sample for parser compatibility.
- `data/raw/sample_airports.csv`: small airport reference fixture.
- `data/raw/sample_weather_daily.csv`: offline weather fixture.
