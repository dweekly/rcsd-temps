#!/usr/bin/env python3
"""
Fetch hourly ASOS data from San Carlos Airport (KSQL) for "feels like" analysis.

This script:
1. Fetches hourly temperature, humidity, dew point, and wind data from Iowa Mesonet
2. Includes pre-calculated "feels like" temperature
3. Aggregates to daily statistics
4. Saves data for trend analysis

Data source: Iowa Environmental Mesonet ASOS archive
Station: SQL (San Carlos Airport, ~3.5 miles from Redwood City)
Period: 1990-present
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
from tqdm import tqdm

API_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = "SQL"  # San Carlos Airport
DATA_DIR = Path("data_raw")
OUT_FILE = DATA_DIR / "asos_sql_hourly.csv"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting: be respectful of the IEM service
REQUEST_DELAY = 0.5  # 500ms between requests


def fetch_asos_data(start_date, end_date):
    """
    Fetch ASOS data for a date range.

    Args:
        start_date: datetime object
        end_date: datetime object

    Returns:
        pandas DataFrame with hourly observations
    """
    # Format dates for API (ISO format with UTC timezone)
    start_str = start_date.strftime("%Y-%m-%dT%H:%M+00:00")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M+00:00")

    params = {
        "station": STATION,
        "data": ["tmpf", "dwpf", "relh", "sknt", "gust", "feel"],
        "sts": start_str,
        "ets": end_str,
        "tz": "UTC",
        "format": "onlycomma",
        "missing": "null",  # Use null for missing values
    }

    try:
        # Add delay to be respectful
        time.sleep(REQUEST_DELAY)

        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()

        # Parse CSV response
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))

        return df

    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to fetch data for {start_date} to {end_date}: {e}")
        return None


def fetch_all_data(start_year=1990, end_year=None):
    """
    Fetch all ASOS data from start_year to present in monthly chunks.

    Args:
        start_year: First year to fetch (default 1990)
        end_year: Last year to fetch (default current year)
    """
    if end_year is None:
        end_year = datetime.now().year

    print(f"Fetching ASOS data from San Carlos Airport (SQL)")
    print(f"Period: {start_year} to {end_year}")
    print(f"This will take several minutes due to rate limiting...")

    all_data = []

    # Fetch data month by month to avoid timeout issues
    current_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year + 1, 1, 1)

    # Calculate total months for progress bar
    total_months = (end_year - start_year + 1) * 12

    with tqdm(total=total_months, desc="Fetching months") as pbar:
        while current_date < end_date:
            # Calculate end of current month
            if current_date.month == 12:
                next_month = datetime(current_date.year + 1, 1, 1)
            else:
                next_month = datetime(current_date.year, current_date.month + 1, 1)

            # Fetch data for this month
            df = fetch_asos_data(current_date, next_month)

            if df is not None and len(df) > 0:
                all_data.append(df)

            # Move to next month
            current_date = next_month
            pbar.update(1)

    if not all_data:
        raise RuntimeError("No data retrieved from ASOS API")

    # Combine all monthly data
    combined_df = pd.concat(all_data, ignore_index=True)

    print(f"\nTotal hourly records fetched: {len(combined_df):,}")

    return combined_df


def process_and_save(df):
    """
    Process hourly data and save to file.

    Args:
        df: DataFrame with hourly ASOS observations
    """
    print("\nProcessing hourly data...")

    # Convert 'valid' column to datetime
    df["datetime"] = pd.to_datetime(df["valid"])
    df["date"] = df["datetime"].dt.date

    # Replace 'null' strings with actual NaN
    numeric_cols = ["tmpf", "dwpf", "relh", "sknt", "gust", "feel"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Save hourly data
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved hourly data: {OUT_FILE}")

    # Create daily aggregations
    print("\nCreating daily aggregations...")

    daily_stats = df.groupby("date").agg({
        "tmpf": ["max", "min", "mean"],
        "dwpf": ["max", "min", "mean"],
        "relh": ["max", "min", "mean"],
        "sknt": ["max", "mean"],
        "gust": "max",
        "feel": ["max", "min", "mean"],
    }).reset_index()

    # Flatten column names
    daily_stats.columns = ['_'.join(col).strip('_') for col in daily_stats.columns.values]
    daily_stats.rename(columns={"date_": "date"}, inplace=True)

    # Save daily stats
    daily_file = DATA_DIR / "asos_sql_daily.csv"
    daily_stats.to_csv(daily_file, index=False)
    print(f"Saved daily statistics: {daily_file}")

    # Print summary
    print("\nData summary:")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Total days: {len(daily_stats)}")
    print(f"  Temperature range: {df['tmpf'].min():.1f}°F to {df['tmpf'].max():.1f}°F")
    print(f"  'Feels like' range: {df['feel'].min():.1f}°F to {df['feel'].max():.1f}°F")

    # Data completeness
    for col in ["tmpf", "feel", "relh", "sknt"]:
        if col in df.columns:
            missing_pct = (df[col].isna().sum() / len(df)) * 100
            print(f"  {col} missing: {missing_pct:.1f}%")

    return daily_stats


def main():
    """Main execution function."""
    print("=" * 70)
    print("ASOS Data Fetcher - San Carlos Airport (SQL)")
    print("For 'Feels Like' Temperature Analysis")
    print("=" * 70)

    # Check if data already exists
    if OUT_FILE.exists():
        print(f"\nFound existing data: {OUT_FILE}")
        response = input("Re-fetch data from server? This will take several minutes. (y/N): ")
        if response.lower() != 'y':
            print("Using existing data. Delete the file to force re-fetch.")
            df = pd.read_csv(OUT_FILE)
            process_and_save(df)
            return

    # Fetch all data
    df = fetch_all_data(start_year=1990)

    # Process and save
    process_and_save(df)

    print("\n" + "=" * 70)
    print("ASOS data fetch complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
