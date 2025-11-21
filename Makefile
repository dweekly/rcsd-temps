.PHONY: all setup fetch normalize visualize analyze visualize-only fetch-feels-like analyze-feels-like analyze-humidity-wind all-feels-like clean help

# Use the Python from the virtual environment
PYTHON = .venv/bin/python

# Default target: run entire pipeline
all: fetch normalize visualize analyze

# Run all analyses (temperature + feels-like + humidity/wind)
all-feels-like: all fetch-feels-like analyze-feels-like analyze-humidity-wind

# Run visualization only (uses committed processed data)
visualize-only: visualize analyze analyze-feels-like analyze-humidity-wind

# Set up the virtual environment and install dependencies
setup:
	@echo "Setting up Python virtual environment..."
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "Setup complete! Virtual environment created in .venv/"

# Fetch data from NOAA API
fetch:
	@echo "Fetching temperature data from NOAA..."
	$(PYTHON) src/fetch_noaa.py

# Normalize and process data
normalize:
	@echo "Normalizing temperature data..."
	$(PYTHON) src/normalize.py

# Generate visualizations
visualize:
	@echo "Generating visualizations..."
	$(PYTHON) src/visualize.py

# Analyze heat trends
analyze:
	@echo "Analyzing heat trends..."
	$(PYTHON) src/analyze_heat_trends.py

# Fetch ASOS data for 'feels like' analysis
fetch-feels-like:
	@echo "Fetching ASOS data from San Carlos Airport..."
	$(PYTHON) src/fetch_feels_like.py

# Analyze 'feels like' temperature trends
analyze-feels-like:
	@echo "Analyzing 'feels like' temperature trends..."
	$(PYTHON) src/analyze_feels_like.py

# Analyze humidity and wind trends
analyze-humidity-wind:
	@echo "Analyzing humidity and wind trends..."
	$(PYTHON) src/analyze_humidity_wind.py

# Clean all generated data and figures
clean:
	@echo "Cleaning generated files..."
	rm -rf data_raw data_processed figures
	@echo "Clean complete!"

# Clean everything including virtual environment
clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf .venv
	@echo "Full clean complete!"

# Show help
help:
	@echo "Redwood City Temperature Visualization Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup                - Create virtual environment and install dependencies"
	@echo "  make fetch                - Download data from NOAA API"
	@echo "  make normalize            - Process and normalize the data"
	@echo "  make visualize            - Generate temperature visualizations"
	@echo "  make analyze              - Analyze heat trends (days above 90°F/100°F)"
	@echo "  make fetch-feels-like     - Download ASOS data for 'feels like' analysis"
	@echo "  make analyze-feels-like   - Analyze 'feels like' temperature trends"
	@echo "  make analyze-humidity-wind- Analyze humidity and wind trends"
	@echo "  make all                  - Run entire temperature pipeline"
	@echo "  make all-feels-like       - Run all pipelines (temp + feels-like + humidity/wind)"
	@echo "  make visualize-only       - Regenerate visualizations using committed data (no API needed)"
	@echo "  make clean                - Remove generated data and figures"
	@echo "  make clean-all            - Remove generated files AND virtual environment"
	@echo "  make help                 - Show this help message"
	@echo ""
	@echo "Quick start (with NOAA API token):"
	@echo "  1. Create .env file with your NOAA_TOKEN"
	@echo "  2. make setup"
	@echo "  3. make all"
	@echo ""
	@echo "Quick start (without API token, using committed data):"
	@echo "  1. make setup"
	@echo "  2. make visualize-only"
