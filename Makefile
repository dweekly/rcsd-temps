.PHONY: all setup fetch normalize visualize clean help

# Use the Python from the virtual environment
PYTHON = .venv/bin/python

# Default target: run entire pipeline
all: fetch normalize visualize

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
	@echo "  make setup      - Create virtual environment and install dependencies"
	@echo "  make fetch      - Download data from NOAA API"
	@echo "  make normalize  - Process and normalize the data"
	@echo "  make visualize  - Generate temperature visualizations"
	@echo "  make all        - Run entire pipeline (fetch + normalize + visualize)"
	@echo "  make clean      - Remove generated data and figures"
	@echo "  make clean-all  - Remove generated files AND virtual environment"
	@echo "  make help       - Show this help message"
	@echo ""
	@echo "Quick start:"
	@echo "  1. Create .env file with your NOAA_TOKEN"
	@echo "  2. make setup"
	@echo "  3. make all"
