PYTHON ?= python
export PYTHONPATH := src
DB ?= data/processed/bird_strikes.sqlite
SAMPLE ?= data/raw/sample_wildlife_strikes.csv
AIRPORTS ?= data/raw/sample_airports.csv
WEATHER ?= data/raw/sample_weather_daily.csv

.PHONY: all compile test init load-airports load-sample load-weather-sample dq summary export-mart sample enrich-weather clean

all: compile test init load-airports load-sample load-weather-sample dq summary export-mart

compile:
	$(PYTHON) -m compileall src dags

test:
	$(PYTHON) -m unittest discover -s tests -v

init:
	$(PYTHON) -m bird_strike_weather.cli init-db --db $(DB)

load-airports:
	$(PYTHON) -m bird_strike_weather.cli load-airports --db $(DB) --csv $(AIRPORTS)

load-sample:
	$(PYTHON) -m bird_strike_weather.cli load-strikes-csv --db $(DB) --csv $(SAMPLE)

load-weather-sample:
	$(PYTHON) -m bird_strike_weather.cli load-weather-csv --db $(DB) --csv $(WEATHER)

dq:
	$(PYTHON) -m bird_strike_weather.cli dq --db $(DB)

summary:
	$(PYTHON) -m bird_strike_weather.cli summary --db $(DB)

export-mart:
	$(PYTHON) -m bird_strike_weather.cli export-mart --db $(DB) --output data/processed/mart_daily_strike_weather.csv

sample: init load-airports load-sample load-weather-sample dq summary export-mart

enrich-weather:
	$(PYTHON) -m bird_strike_weather.cli enrich-weather --db $(DB) --limit 10

clean:
	$(PYTHON) -c "from pathlib import Path; p=Path('$(DB)'); p.unlink() if p.exists() else None"
