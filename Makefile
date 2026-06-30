PYTHON ?= python
DB ?= data/processed/bird_strikes.sqlite
SAMPLE ?= data/raw/sample_wildlife_strikes.csv
AIRPORTS ?= data/raw/sample_airports.csv
WEATHER ?= data/raw/sample_weather_daily.csv

.PHONY: all compile test init load-airports load-sample load-weather-sample dq summary export-mart sample enrich-weather clean

all: compile test init load-airports load-sample load-weather-sample dq summary export-mart

compile:
	$(PYTHON) -m compileall src dags

test:
	$(PYTHON) -m unittest discover -s tests

init:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'init-db', '--db', '$(DB)']; main()"

load-airports:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'load-airports', '--db', '$(DB)', '--csv', '$(AIRPORTS)']; main()"

load-sample:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'load-strikes-csv', '--db', '$(DB)', '--csv', '$(SAMPLE)']; main()"

load-weather-sample:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'load-weather-csv', '--db', '$(DB)', '--csv', '$(WEATHER)']; main()"

dq:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'dq', '--db', '$(DB)']; main()"

summary:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'summary', '--db', '$(DB)']; main()"

export-mart:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'export-mart', '--db', '$(DB)', '--output', 'data/processed/mart_daily_strike_weather.csv']; main()"

sample: init load-airports load-sample load-weather-sample dq summary export-mart

enrich-weather:
	$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from bird_strike_weather.cli import main; sys.argv=['cli', 'enrich-weather', '--db', '$(DB)', '--limit', '10']; main()"

clean:
	$(PYTHON) -c "from pathlib import Path; p=Path('$(DB)'); p.unlink() if p.exists() else None"
