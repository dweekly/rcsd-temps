# Redwood City Temperature Extremes Visualization

A data visualization project that analyzes and visualizes daily temperature extremes (highs and lows) for Redwood City, California, using NOAA's Global Historical Climatology Network Daily (GHCN-D) dataset.

## Overview

This project creates beautiful visualizations showing how recent years' temperatures compare to historical patterns. Each visualization shows:

- **Historical Context**: All years from ~1948 onwards plotted as faint gray lines
- **Recent Trends**: The last 3 years highlighted in color for easy comparison
- **Daily Extremes**: Both daily high (TMAX) and daily low (TMIN) temperatures
- **Seasonal Patterns**: Month-by-month temperature variations throughout the year

## Sample Output

The pipeline generates high-resolution visualizations in multiple formats (PNG, PDF, SVG) showing two panels:
- Top panel: Daily high temperatures
- Bottom panel: Daily low temperatures

## Requirements

- macOS (or Linux with minor modifications)
- Python 3.8 or later
- NOAA NCEI API token (free, see setup below)
- `make` (usually pre-installed on macOS)

## Quick Start

### 1. Get a NOAA API Token

1. Visit [NOAA NCEI's token request page](https://www.ncdc.noaa.gov/cdo-web/token)
2. Enter your email address
3. Check your email for the token (arrives within minutes)

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/dweekly/rcsd-temps.git
cd rcsd-temps

# Create .env file with your token
echo "NOAA_TOKEN=your-token-here" > .env

# Set up virtual environment and install dependencies
make setup
```

### 3. Run the Pipeline

```bash
# Run the entire pipeline (fetch, process, visualize)
make all
```

This will:
1. Download temperature data from NOAA (~1948 to present)
2. Process and normalize the data
3. Generate visualizations in the `figures/` directory

## Project Structure

```
rcsd-temps/
├── src/
│   ├── fetch_noaa.py      # Download data from NOAA API
│   ├── normalize.py       # Process and normalize data
│   └── visualize.py       # Generate visualizations
├── data_raw/              # Raw API responses (generated)
├── data_processed/        # Processed CSV files (generated)
├── figures/               # Output visualizations (generated)
├── .env                   # API token (create this, not in git)
├── .gitignore            # Excludes generated files and secrets
├── Makefile              # Pipeline automation
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Detailed Usage

### Individual Pipeline Steps

You can run each step independently:

```bash
# Download data from NOAA
make fetch

# Process the downloaded data
make normalize

# Generate visualizations
make visualize
```

### Cleaning Up

```bash
# Remove generated data and figures (keeps venv)
make clean

# Remove everything including virtual environment
make clean-all
```

### Help

```bash
# Show all available commands
make help
```

## How It Works

### 1. Data Fetching (`fetch_noaa.py`)

- Discovers the Redwood City weather station in NOAA's GHCN-D network
- Downloads all daily TMAX and TMIN records from ~1948 to present
- Caches raw API responses for reproducibility
- Outputs: `data_raw/all_daily_raw.csv`

### 2. Data Normalization (`normalize.py`)

- Converts temperatures from metric to Fahrenheit
- Removes February 29 (leap days) for consistent 365-day years
- Creates day-of-year aligned matrices suitable for visualization
- Performs data quality checks
- Outputs:
  - `data_processed/daily_clean.csv` - Tidy daily temperature data
  - `data_processed/tmax_matrix.csv` - Daily highs (365 days × N years)
  - `data_processed/tmin_matrix.csv` - Daily lows (365 days × N years)

### 3. Visualization (`visualize.py`)

- Loads processed temperature matrices
- Creates two-panel matplotlib figure
- Plots all historical years in gray
- Highlights recent years in color (orange/red for highs, blue for lows)
- Adds month labels, legends, and annotations
- Saves high-resolution outputs (PNG at 500 DPI, plus PDF and SVG)

## Data Source

This project uses the **NOAA Global Historical Climatology Network Daily (GHCN-D)** dataset, accessed via the NCEI Climate Data Online (CDO) API v2.

- **Dataset**: GHCND
- **Station**: Automatically discovered (typically USC00044715 - Redwood City)
- **Parameters**: TMAX (daily maximum temperature), TMIN (daily minimum temperature)
- **Period**: ~1948 to present
- **API Documentation**: https://www.ncdc.noaa.gov/cdo-web/webservices/v2

## Customization

### Change the Number of Highlighted Years

Edit `src/visualize.py` and modify the `num_highlight` parameter in the `main()` function.

### Adjust Visual Styling

Colors, line widths, and other styling options can be modified in `src/visualize.py` in the `plot_panel()` function.

### Different Location

To analyze a different location, modify `src/fetch_noaa.py`:
- Change the `locationid` parameter to a different FIPS code
- Update the station search criteria

## Future Enhancements

- [ ] Support for any ZIP code or city name
- [ ] Interactive web-based visualizations (Plotly/Altair)
- [ ] Additional metrics (days above/below thresholds, trends)
- [ ] Automated monthly updates via GitHub Actions
- [ ] School-year specific analysis (Aug-Jun)
- [ ] Comparison with other Bay Area cities

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - feel free to use and modify for your own projects.

## Acknowledgments

- NOAA National Centers for Environmental Information for providing free access to climate data
- The GHCN-D dataset maintainers for decades of careful temperature record keeping

## Contact

Created by [@dweekly](https://github.com/dweekly)

---

Made with ❤️ for the Redwood City community
