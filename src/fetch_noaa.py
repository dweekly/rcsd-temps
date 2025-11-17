#!/usr/bin/env python3
"""
Fetch daily temperature data from NOAA GHCN-D API for Redwood City, CA.

This script:
1. Discovers the appropriate NOAA GHCN-D station for Redwood City
2. Fetches all daily TMAX and TMIN records from ~1948 to present
3. Saves raw API responses and a consolidated CSV
"""

import os
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import date
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
DATA_DIR = Path("data_raw")
PAGES_DIR = DATA_DIR / "noaa_pages"
PAGES_DIR.mkdir(parents=True, exist_ok=True)


def get_api_headers():
    """Get API headers with token from environment variable."""
    token = os.environ.get("NOAA_TOKEN")
    if not token:
        raise RuntimeError(
            "NOAA_TOKEN environment variable not set. "
            "Please set it in your .env file or shell environment."
        )
    return {"token": token}


def find_station():
    """
    Find the NOAA GHCN-D station for Redwood City, CA.

    Returns:
        str: Station ID (e.g., 'GHCND:USC00044715')
    """
    print("Searching for Redwood City weather station...")

    # San Mateo County FIPS code is 06081
    params = {
        "datasetid": "GHCND",
        "locationid": "FIPS:06081",  # San Mateo County, CA
        "limit": 1000,
    }

    try:
        r = requests.get(
            f"{BASE_URL}/stations",
            headers=get_api_headers(),
            params=params,
            timeout=30
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to query NOAA stations API: {e}")

    data = r.json()
    stations = data.get("results", [])

    # Filter for Redwood City
    candidates = [
        s for s in stations
        if "REDWOOD" in s["name"].upper() and "CITY" in s["name"].upper()
    ]

    if not candidates:
        raise RuntimeError(
            "No Redwood City station found in GHCN-D dataset. "
            "Available stations in San Mateo County:\n" +
            "\n".join(f"  - {s['name']} ({s['id']})" for s in stations[:10])
        )

    station = candidates[0]
    station_id = station["id"]

    print(f"Found station: {station['name']}")
    print(f"  ID: {station_id}")
    print(f"  Coverage: {station.get('mindate', 'N/A')} to {station.get('maxdate', 'N/A')}")

    # Save station info
    station_info_file = DATA_DIR / "station_info.json"
    with open(station_info_file, "w") as f:
        json.dump(station, f, indent=2)
    print(f"Saved station info to {station_info_file}")

    return station_id


def fetch_data(station_id, start_date="1948-01-01", end_date=None):
    """
    Fetch all daily TMAX and TMIN data for a station.

    Args:
        station_id: NOAA station ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to today
    """
    if end_date is None:
        end_date = date.today().isoformat()

    print(f"\nFetching data from {start_date} to {end_date}...")

    offset = 1
    all_rows = []

    with tqdm(desc="Fetching API pages", unit="page") as pbar:
        while True:
            params = {
                "datasetid": "GHCND",
                "stationid": station_id,
                "startdate": start_date,
                "enddate": end_date,
                "datatypeid": "TMAX,TMIN",  # Both TMAX and TMIN
                "limit": 1000,
                "offset": offset,
                "units": "metric",  # Get data in metric (tenths of °C)
            }

            try:
                r = requests.get(
                    f"{BASE_URL}/data",
                    headers=get_api_headers(),
                    params=params,
                    timeout=30
                )
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"\nWarning: API request failed at offset {offset}: {e}")
                break

            data = r.json()
            results = data.get("results", [])

            if not results:
                break

            # Cache raw response
            page_file = PAGES_DIR / f"page_{offset:06d}.json"
            with open(page_file, "w") as f:
                json.dump(data, f)

            all_rows.extend(results)
            offset += 1000
            pbar.update(1)

    if not all_rows:
        raise RuntimeError("No data retrieved from NOAA API")

    print(f"\nTotal records fetched: {len(all_rows):,}")

    # Convert to DataFrame and save
    df = pd.DataFrame(all_rows)
    output_file = DATA_DIR / "all_daily_raw.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved raw data to {output_file}")

    # Print summary
    print("\nData summary:")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Data types: {df['datatype'].unique().tolist()}")
    print(f"  Total records: {len(df):,}")

    return df


def main():
    """Main execution function."""
    print("=" * 70)
    print("NOAA GHCN-D Data Fetcher for Redwood City, CA")
    print("=" * 70)

    # Check if we already have station info cached
    station_info_file = DATA_DIR / "station_info.json"
    if station_info_file.exists():
        print(f"\nLoading cached station info from {station_info_file}")
        with open(station_info_file) as f:
            station_info = json.load(f)
            station_id = station_info["id"]
            print(f"Using station: {station_info['name']} ({station_id})")
    else:
        station_id = find_station()

    # Fetch the data
    fetch_data(station_id)

    print("\n" + "=" * 70)
    print("Data fetch complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
