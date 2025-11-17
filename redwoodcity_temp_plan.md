# Redwood City Temperature Extremes Visualization – Engineering Plan

This document describes a complete, reproducible engineering plan to:
- Download daily minimum and maximum temperature data for Redwood City, California (from the late 1940s onward) from NOAA’s GHCN-D dataset.
- Normalize and structure the data into aligned daily time series.
- Generate a high‑resolution visualization showing all years in faint gray, with the last 2–3 years highlighted in color.
- Package the work so it can live in a public GitHub repository and be rerun on a macOS machine **without polluting the global Python environment** (using `venv`).

Assumptions:
- You’re running on a reasonably beefy macOS machine.
- You’re comfortable installing open‑source tools via Homebrew.
- You have a NOAA NCEI API token available as an environment variable `NOAA_TOKEN`.
- A fast internet connection is available (API calls will be trivial in volume).

---

## 1. High‑Level Architecture

The project is organized into three main components:

1. **Data Fetcher (`fetch_noaa.py`)**
   - Discovers the appropriate NOAA GHCN‑D station for Redwood City.
   - Pulls daily records (TMAX, TMIN) from ~1948 to present via the NOAA CDO API.
   - Writes raw responses and a consolidated long‑format CSV to `data_raw/`.

2. **Data Normalizer (`normalize.py`)**
   - Reads the long‑format CSV.
   - Converts raw measurements to Fahrenheit.
   - Aligns each year by day‑of‑year, handling leap days and missing data.
   - Outputs clean “matrix” CSVs (365 rows × N years) for both TMAX and TMIN, plus a tidy daily table.

3. **Visualizer (`visualize.py`)**
   - Loads the processed matrices and daily table.
   - Produces a two‑panel figure (daily highs and daily lows) with:
     - All years plotted as thin, semi‑transparent gray lines.
     - The last 2–3 years emphasized with thicker, colored lines.
     - Labels and annotations for recent years and record extremes.
   - Saves a high‑resolution PNG (and optionally PDF/SVG) suitable for publication.

All of this is wired together by a simple `Makefile` or equivalent orchestration script.

---

## 2. Toolchain & Environment (with `venv`)

### 2.1 Homebrew dependencies

Install base tools via Homebrew (these are system‑level and not Python‑specific):

```bash
# If needed, install Homebrew itself first (macOS)
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew update
brew install python git wget
```

`wget` is optional (handy for debugging). Python from Homebrew gives you a modern `python3`.

### 2.2 Project directory layout

Create a new project folder that will later become a GitHub repository, e.g.:

```bash
mkdir redwoodcity-climate
cd redwoodcity-climate
```

Proposed structure:

```text
redwoodcity-climate/
├── data_raw/             # Raw API responses & intermediate CSVs
├── data_processed/       # Cleaned tables & matrices
├── src/
│   ├── fetch_noaa.py
│   ├── normalize.py
│   ├── visualize.py
│   └── config.py
├── env/                  # (optional) non-Python env helpers
├── Makefile
├── README.md
└── requirements.txt
```

`data_raw/` and `data_processed/` will be in `.gitignore` or treated as generated artifacts.

### 2.3 Python virtual environment (no global pollution)

Create and use a local `venv` inside the project:

```bash
cd redwoodcity-climate

# Create a virtual environment
python3 -m venv .venv

# Activate it (macOS / bash / zsh)
source .venv/bin/activate

# Upgrade pip inside the venv
pip install --upgrade pip
```

Everything that follows (`pip install`, running scripts) should be done with the venv **activated**, so all Python packages live inside `.venv` and not in the global Python environment.

### 2.4 Python dependencies

Create `requirements.txt` with something like:

```text
pandas
numpy
matplotlib
requests
python-dateutil
tqdm
```

Then install inside the venv:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Optional (for interactive work or extra styling):

```text
seaborn
jupyter
```

---

## 3. Data Source and Station Selection (NOAA GHCN‑D)

We’ll use NOAA’s **Global Historical Climatology Network – Daily** (“GHCND”) dataset, accessed via the NCEI CDO API.

### 3.1 NOAA API token

Obtain a token from NCEI’s “Request a Token” page (done already). Set it in your shell environment:

```bash
export NOAA_TOKEN="your-actual-token-here"
```

You may want to put this in your shell profile (`~/.zshrc`, `~/.bashrc`) for convenience.

### 3.2 Discovering the Redwood City station programmatically

Rather than hard‑coding the station ID, use the `/stations` API endpoint to search within San Mateo County and filter for “Redwood City”.

Example logic:
- Query: `locationid=FIPS:06081` (San Mateo County, CA)
- Dataset: `GHCND`
- Then filter returned station metadata by name containing “REDWOOD” and “CITY”.

This will likely yield something like `GHCND:USC00044715` (or similar coop station).

**In `src/fetch_noaa.py`:**

- Have a function `find_station()` that:
  - calls the stations endpoint,
  - filters for Redwood City,
  - returns the station ID string.

You can cache this in `data_raw/station_info.json` for later runs.

---

## 4. Component A – Data Fetcher (`fetch_noaa.py`)

### 4.1 Responsibilities

- Find Redwood City’s GHCN station ID.
- Download all daily records from ~1948‑01‑01 to the most recent date available.
- Limit to `TMAX` and `TMIN` datatypes.
- Save raw JSON pages to `data_raw/noaa_pages/`.
- Produce a consolidated long‑format CSV: `data_raw/all_daily.csv`.

### 4.2 API strategy

Endpoint:

```text
GET https://www.ncdc.noaa.gov/cdo-web/api/v2/data
```

Parameters for data:
- `datasetid=GHCND`
- `stationid=<discovered station>`
- `startdate=1948-01-01`
- `enddate=<today or last-known date>`
- `datatypeid=TMAX`
- `datatypeid=TMIN`
- `units=standard` (or `metric`; we’ll convert if necessary)
- `limit=1000`
- `offset` for pagination

Authentication: HTTP header `token: $NOAA_TOKEN`.

### 4.3 Pseudocode outline

```python
import os
import requests
import pandas as pd
from pathlib import Path
from tqdm import tqdm

BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
DATA_DIR = Path("data_raw")
PAGES_DIR = DATA_DIR / "noaa_pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)

def get_api_headers():
    token = os.environ.get("NOAA_TOKEN")
    if not token:
        raise RuntimeError("NOAA_TOKEN env var not set")
    return {"token": token}

def find_station():
    # Query stations within San Mateo County FIPS code 06081
    params = {
        "datasetid": "GHCND",
        "locationid": "FIPS:06081",
        "limit": 1000,
    }
    r = requests.get(f"{BASE_URL}/stations", headers=get_api_headers(), params=params)
    r.raise_for_status()
    stations = r.json().get("results", [])
    candidates = [
        s for s in stations if "REDWOOD" in s["name"].upper() and "CITY" in s["name"].upper()
    ]
    if not candidates:
        raise RuntimeError("No Redwood City station found")
    station = candidates[0]  # pick the first/best
    (DATA_DIR / "station_info.json").write_text(str(station))
    return station["id"]  # e.g. "GHCND:USC00044715"

def fetch_data(station_id, start_date="1948-01-01", end_date=None):
    if end_date is None:
        # you can pick today's date or a fixed end date
        from datetime import date
        end_date = date.today().isoformat()

    offset = 1
    all_rows = []
    pbar = tqdm(desc="Fetching NOAA pages")
    while True:
        params = {
            "datasetid": "GHCND",
            "stationid": station_id,
            "startdate": start_date,
            "enddate": end_date,
            "datatypeid": ["TMAX", "TMIN"],
            "limit": 1000,
            "offset": offset,
            "units": "metric",  # or 'standard'
        }
        r = requests.get(f"{BASE_URL}/data", headers=get_api_headers(), params=params)
        r.raise_for_status()
        data = r.json().get("results", [])
        if not data:
            break
        # cache raw
        (PAGES_DIR / f"page_{offset}.json").write_text(r.text)
        all_rows.extend(data)
        offset += 1000
        pbar.update(1)

    pbar.close()

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)
    df.to_csv(DATA_DIR / "all_daily_raw.csv", index=False)

if __name__ == "__main__":
    station_id = find_station()
    fetch_data(station_id)
```

### 4.4 Notes

- Using `units=metric` simplifies conversion: NOAA returns `value` in tenths of °C; we explicitly convert later.
- Pagination is via `offset`. We fetch pages until we get an empty result set.
- Raw pages are kept for debugging / re‑processing (`page_*.json`).

---

## 5. Component B – Data Normalizer (`normalize.py`)

### 5.1 Responsibilities

- Read `data_raw/all_daily_raw.csv`.
- Filter to `TMAX` and `TMIN`.
- Convert values to °F.
- Add derived columns: `year`, `month`, `day`, `doy` (day‑of‑year).
- Remove February 29 to ensure each year is 365 points.
- Pivot into two matrices:
  - `tmax_matrix.csv`: rows = `doy`, columns = `year`
  - `tmin_matrix.csv`: same
- Produce a tidy `data_processed/daily_clean.csv` for general use.

### 5.2 Handling leap years and missing data

- **Leap day (Feb 29)**: drop rows where `month == 2` and `day == 29`, or where `doy` corresponds to Feb 29.
- **Missing days**:
  - If a year has a small number of missing days (e.g. `<= 10`), leave them as NaN; matplotlib will simply skip that part of the line.
  - If a year has large gaps (e.g. `> 30` missing days), consider excluding it from visualization or marking it as incomplete.
- For the Redwood City coop station, we expect data to be fairly complete from late 1940s onward.

### 5.3 Pseudocode outline

```python
import pandas as pd
from pathlib import Path

RAW_CSV = Path("data_raw/all_daily_raw.csv")
OUT_DIR = Path("data_processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    df = pd.read_csv(RAW_CSV)
    # Keep only TMAX/TMIN
    df = df[df["datatype"].isin(["TMAX", "TMIN"])]

    # Convert date
    df["date"] = pd.to_datetime(df["date"])

    # NOAA metric: value in tenths of °C; confirm from docs
    df["temp_c"] = df["value"] / 10.0
    df["temp_f"] = df["temp_c"] * 9.0 / 5.0 + 32.0

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day

    # Create day-of-year (doy) and drop Feb 29
    df["doy"] = df["date"].dt.dayofyear

    # Drop Feb 29 (simplest and visually cleanest)
    is_leap_day = (df["month"] == 2) & (df["day"] == 29)
    df = df[~is_leap_day]

    # Save tidy daily table for reference
    daily_cols = ["date", "year", "month", "day", "doy", "datatype", "temp_f"]
    df[daily_cols].to_csv(OUT_DIR / "daily_clean.csv", index=False)

    # Pivot to matrices
    tmax = df[df["datatype"] == "TMAX"].pivot(index="doy", columns="year", values="temp_f")
    tmin = df[df["datatype"] == "TMIN"].pivot(index="doy", columns="year", values="temp_f")

    tmax.to_csv(OUT_DIR / "tmax_matrix.csv")
    tmin.to_csv(OUT_DIR / "tmin_matrix.csv")

if __name__ == "__main__":
    main()
```

### 5.4 Quality checks

You can add some quick checks in `normalize.py`:
- Print the range of years present in `tmax`/`tmin`.
- Print number of NaNs per year and warn if any year is very incomplete.

---

## 6. Component C – Visualization (`visualize.py`)

### 6.1 Goals

- Create a **two‑panel figure**:
  - Top: daily high temperatures (TMAX) vs. day‑of‑year.
  - Bottom: daily low temperatures (TMIN) vs. day‑of‑year.
- For each panel:
  - Plot each historical year from 1948 up to (N − 3) as a thin, semi‑transparent gray line.
  - Plot the last 3 full years in distinct, more opaque colors with thicker lines.
  - Label only the last 3 years directly on the plot (at the right edge of the lines).
- Use a single x‑axis (1–365), with month labels overlaid.
- Save as a high‑resolution PNG (e.g. 500 DPI) and optionally PDF/SVG.

### 6.2 Determining “last three years”

In `visualize.py`, derive:

```python
years = sorted(tmax.columns)
highlight_years = years[-3:]  # last 3
```

You can make this configurable if you want (e.g. an argument or config entry).

### 6.3 Styling choices

- **Historical years**:
  - Color: medium gray (`#c0c0c0`)
  - Alpha: ~0.25
  - Line width: ~0.4
- **Recent years** (example):
  - Oldest recent (Y‑2): `#ffb347` (light orange), lw=1.3
  - Middle recent (Y‑1): `#ff7f50` (coral), lw=1.7
  - Most recent (Y): `#d7301f` (deep red), lw=2.1
- For lows, you can mirror this with blues (`#9ecae1`, `#4292c6`, `#08519c`) or reuse the same palette but in the bottom panel with clear labeling.
- Figure size: `figsize=(14, 10)` is a good starting point.
- Output: `dpi=400–600` for PNG.

### 6.4 Adding month labels on the x‑axis

We’re plotting by day‑of‑year (1–365). Use a helper that maps approximate month start DOYs:

```python
month_starts = {
    "Jan": 1, "Feb": 32, "Mar": 60, "Apr": 91, "May": 121,
    "Jun": 152, "Jul": 182, "Aug": 213, "Sep": 244, "Oct": 274,
    "Nov": 305, "Dec": 335
}
```

Then:

```python
ax.set_xticks(list(month_starts.values()))
ax.set_xticklabels(list(month_starts.keys()))
```

### 6.5 Optional: School‑year shading

If you want to emphasize the school year roughly (e.g. Aug 15–Jun 5), you can shade that region lightly:

```python
def date_to_doy(month, day):
    import datetime
    year = 2021  # non‑leap year, just for mapping
    return datetime.date(year, month, day).timetuple().tm_yday

school_start_doy = date_to_doy(8, 15)
school_end_doy   = date_to_doy(6, 5)

for ax in (ax1, ax2):
    ax.axvspan(school_start_doy, 365, color="yellow", alpha=0.03, zorder=0)
    ax.axvspan(1, school_end_doy, color="yellow", alpha=0.03, zorder=0)
```

Or simply annotate the school‑year region in text instead of shading if you want cleaner visuals.

### 6.6 Pseudocode outline

```python
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path("data_processed")

def load_matrices():
    tmax = pd.read_csv(DATA_DIR / "tmax_matrix.csv", index_col=0)
    tmin = pd.read_csv(DATA_DIR / "tmin_matrix.csv", index_col=0)
    # rows index = doy, columns = year (as strings or ints)
    tmax.columns = tmax.columns.astype(int)
    tmin.columns = tmin.columns.astype(int)
    return tmax, tmin

def plot_panel(ax, matrix, highlight_years, is_max=True):
    doys = matrix.index.values
    years = sorted(matrix.columns)

    # Historical years
    for yr in years:
        if yr in highlight_years:
            continue
        ax.plot(
            doys,
            matrix[yr].values,
            color="#c0c0c0",
            alpha=0.25,
            linewidth=0.4,
            zorder=1,
        )

    # Highlight years
    color_map = {
        highlight_years[-3]: "#ffb347",
        highlight_years[-2]: "#ff7f50",
        highlight_years[-1]: "#d7301f",
    }
    width_map = {
        highlight_years[-3]: 1.3,
        highlight_years[-2]: 1.7,
        highlight_years[-1]: 2.1,
    }

    for yr in highlight_years:
        ax.plot(
            doys,
            matrix[yr].values,
            color=color_map[yr],
            linewidth=width_map[yr],
            zorder=2,
        )

        # Label at right edge (last valid value)
        y_last = matrix[yr].dropna().iloc[-1]
        ax.text(
            doys[-1] + 1,
            y_last,
            str(yr),
            color=color_map[yr],
            fontsize=9,
            va="center",
        )

    ax.set_ylabel("Temperature (°F)")
    ax.grid(True, color="#eeeeee", linewidth=0.5)

def main():
    tmax, tmin = load_matrices()
    years = sorted(tmax.columns)
    highlight_years = years[-3:]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 10), sharex=True, dpi=300
    )

    plot_panel(ax1, tmax, highlight_years, is_max=True)
    ax1.set_title("Redwood City Daily High Temperatures (TMAX)")

    plot_panel(ax2, tmin, highlight_years, is_max=False)
    ax2.set_title("Redwood City Daily Low Temperatures (TMIN)")

    # Month labels
    month_starts = {
        "Jan": 1, "Feb": 32, "Mar": 60, "Apr": 91, "May": 121,
        "Jun": 152, "Jul": 182, "Aug": 213, "Sep": 244, "Oct": 274,
        "Nov": 305, "Dec": 335
    }
    ax2.set_xticks(list(month_starts.values()))
    ax2.set_xticklabels(list(month_starts.keys()))

    fig.suptitle(
        "Redwood City, CA Daily Temperature Extremes (1948–Present)\n"
        "Each gray line is one year; last three years highlighted in color",
        fontsize=14,
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])

    out_dir = Path("figures")
    out_dir.mkdir(exist_ok=True)
    fig.savefig(out_dir / "redwoodcity_temp_extremes.png", dpi=500)
    fig.savefig(out_dir / "redwoodcity_temp_extremes.pdf")

if __name__ == "__main__":
    main()
```

You can extend this to annotate record highs/lows by scanning the matrices for global maxima/minima and marking those with `ax.annotate`.

---

## 7. Orchestration with `Makefile`

To make the pipeline trivial to run end‑to‑end inside the `venv`, create a `Makefile`:

```makefile
.PHONY: all fetch normalize visualize clean

all: fetch normalize visualize

fetch:
\t. .venv/bin/activate && python src/fetch_noaa.py

normalize:
\t. .venv/bin/activate && python src/normalize.py

visualize:
\t. .venv/bin/activate && python src/visualize.py

clean:
\trm -rf data_raw data_processed figures
```

Notes:
- The `. .venv/bin/activate` (dot‑space) is POSIX shell syntax; it sources the activation script before running Python.
- You can also avoid activation in `Makefile` by calling the venv’s Python directly, e.g. `.venv/bin/python src/fetch_noaa.py` etc., which is often cleaner and avoids shell quirks.

Example using direct venv Python:

```makefile
PYTHON = .venv/bin/python

fetch:
\t$(PYTHON) src/fetch_noaa.py

normalize:
\t$(PYTHON) src/normalize.py

visualize:
\t$(PYTHON) src/visualize.py
```

That’s typically more robust.

---

## 8. Running the Whole Pipeline

1. **Clone/init repo and create venv**

```bash
git clone <your-github-url>.git redwoodcity-climate
cd redwoodcity-climate

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. **Set NOAA token**

```bash
export NOAA_TOKEN="your-token-here"
```

3. **Run entire pipeline**

```bash
make all
```

This will:

- Discover and fetch data from NOAA → `data_raw/`
- Normalize and pivot → `data_processed/`
- Produce visualizations → `figures/redwoodcity_temp_extremes.png` (and `.pdf`).

4. **Inspect the output**

Open the PNG in Preview or your favorite viewer; you should see:

- Gray “spaghetti” of historical daily highs/lows.
- The latest three years in bright color, clearly labeled at the right.
- Seasonal pattern over the year, with recent years’ extremes relative to historical ranges.

---

## 9. Validation & Sanity Checks

Before trusting the visualization, perform these checks:

1. **Data coverage**  
   - Inspect `data_processed/daily_clean.csv`:
     - Confirm years range from ~1948 to the last full year.
     - Confirm minimal missing days per year.

2. **Extremes**  
   - Compute global max/min of TMAX/TMIN across the dataset and verify they match known Redwood City records (e.g. ~110°F highs, ~16°F lows).

3. **Plot sanity**  
   - Confirm that the seasonal “shape” is sensible (cool winters, warm summers, increased variability in shoulder seasons).
   - Ensure highlighted years line up where expected (e.g., known heat waves, etc.).

---

## 10. Future Enhancements (Post‑MVP)

Once the basic pipeline works, you can iterate in several directions:

- **Interactive visualizations**: Export processed data and use Plotly, Altair, or a web frontend to allow year filtering, hover tooltips, etc.
- **Additional metrics**:
  - Number of days above/below thresholds (e.g. >90°F, >100°F) per year.
  - School‑year‑specific stats (Aug–Jun only).
- **Automated updates**: A GitHub Actions workflow that runs monthly or annually to pull new NOAA data, regenerate visualizations, and commit artifacts to the repo.
- **Alternative views**:
  - Density plots by day‑of‑year (e.g. percentile envelopes instead of individual gray lines).
  - Rolling averages or trend lines on top of daily extremes.

---

## 11. Summary

- The entire pipeline is self‑contained within a project directory, using a **local Python virtual environment** (`.venv`) so your system Python remains untouched.
- Data is fetched once from NOAA’s CDO API (with caching) and then processed and visualized using standard Python data science tooling.
- The final artifact is a high‑resolution PNG (and optionally PDF) that shows how the last few years of daily temperature extremes compare with several decades of history in Redwood City.

Once this is in a GitHub repo, anyone with `python3`, `make`, and a NOAA token can reproduce the exact visualization by following the same steps and staying within the venv. 
