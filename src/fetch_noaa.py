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
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import date
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Rate limiting: NOAA API allows 5 requests per second
REQUEST_DELAY = 0.21  # 210ms between requests = ~4.7 requests/second

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
        dict: Station information including ID and date coverage
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

    # Sort by coverage start date (prefer older stations) and prioritize COOP stations
    def station_score(s):
        mindate = s.get("mindate", "9999-12-31")
        # Prefer USC (COOP) stations over US1 (citizen weather observers)
        station_type_bonus = 0 if s["id"].startswith("GHCND:USC") else 1000
        return (station_type_bonus, mindate)

    candidates.sort(key=station_score)
    station = candidates[0]

    print(f"Found station: {station['name']}")
    print(f"  ID: {station['id']}")
    print(f"  Coverage: {station.get('mindate', 'N/A')} to {station.get('maxdate', 'N/A')}")

    # Save station info
    station_info_file = DATA_DIR / "station_info.json"
    with open(station_info_file, "w") as f:
        json.dump(station, f, indent=2)
    print(f"Saved station info to {station_info_file}")

    return station


def fetch_data_for_type(station, datatype):
    """
    Fetch all daily data for a specific data type.

    Args:
        station: Station dict with id, mindate, maxdate
        datatype: Either "TMAX" or "TMIN"

    Returns:
        list: All records for this datatype
    """
    from datetime import datetime, timedelta

    station_id = station["id"]
    # Use 1948 as start date or station's mindate if later
    station_mindate = station.get("mindate", "1948-01-01")
    start_date = max("1948-01-01", station_mindate)
    end_date = station.get("maxdate", date.today().isoformat())

    # Parse dates
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    all_rows = []
    page_num = 0

    # Fetch data in 1-year chunks to avoid API limits
    current_start = start_dt

    while current_start < end_dt:
        # Get data for 1 year at a time
        current_end = min(
            datetime(current_start.year + 1, 1, 1) - timedelta(days=1),
            end_dt
        )

        chunk_start = current_start.date().isoformat()
        chunk_end = current_end.date().isoformat()

        offset = 1
        while True:
            params = {
                "datasetid": "GHCND",
                "stationid": station_id,
                "startdate": chunk_start,
                "enddate": chunk_end,
                "datatypeid": datatype,
                "limit": 1000,
                "offset": offset,
                "units": "metric",  # Get data in metric (tenths of °C)
            }

            try:
                # Add rate limiting delay
                time.sleep(REQUEST_DELAY)

                r = requests.get(
                    f"{BASE_URL}/data",
                    headers=get_api_headers(),
                    params=params,
                    timeout=30
                )
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                # Silently skip failed chunks (might be no data for that period)
                break

            data = r.json()
            results = data.get("results", [])

            if not results:
                break

            # Cache raw response
            page_file = PAGES_DIR / f"page_{datatype}_{page_num:06d}.json"
            with open(page_file, "w") as f:
                json.dump(data, f)

            all_rows.extend(results)
            page_num += 1
            offset += 1000

        # Move to next year
        current_start = datetime(current_start.year + 1, 1, 1)

    return all_rows


def fetch_data(station):
    """
    Fetch all daily TMAX and TMIN data for a station.

    Args:
        station: Station dict with id, mindate, maxdate
    """
    # Use 1948 as start date or station's mindate if later
    station_mindate = station.get("mindate", "1948-01-01")
    start_date = max("1948-01-01", station_mindate)
    end_date = station.get("maxdate", date.today().isoformat())

    print(f"\nFetching data from {start_date} to {end_date}...")

    # Fetch TMAX and TMIN separately
    print("\nFetching TMAX (daily highs)...")
    tmax_rows = fetch_data_for_type(station, "TMAX")
    print(f"  Retrieved {len(tmax_rows):,} TMAX records")

    print("\nFetching TMIN (daily lows)...")
    tmin_rows = fetch_data_for_type(station, "TMIN")
    print(f"  Retrieved {len(tmin_rows):,} TMIN records")

    all_rows = tmax_rows + tmin_rows

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

    # Check if we already have the final CSV file
    output_file = DATA_DIR / "all_daily_raw.csv"
    if output_file.exists():
        print(f"\nFound existing data file: {output_file}")
        print("Skipping fetch (data already downloaded)")
        print("Delete this file to re-fetch data from NOAA")

        # Load and print summary
        df = pd.read_csv(output_file)
        print("\nExisting data summary:")
        print(f"  Total records: {len(df):,}")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"  Data types: {df['datatype'].unique().tolist()}")

        print("\n" + "=" * 70)
        print("Using cached data!")
        print("=" * 70)
        return

    # Check if we already have station info cached
    station_info_file = DATA_DIR / "station_info.json"
    if station_info_file.exists():
        print(f"\nLoading cached station info from {station_info_file}")
        with open(station_info_file) as f:
            station = json.load(f)
            print(f"Using station: {station['name']} ({station['id']})")
    else:
        station = find_station()

    # Fetch the data
    fetch_data(station)

    print("\n" + "=" * 70)
    print("Data fetch complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
