#!/usr/bin/env python3
"""
Normalize and structure temperature data for visualization.

This script:
1. Reads raw NOAA data CSV
2. Converts temperatures to Fahrenheit
3. Aligns data by day-of-year (removing Feb 29)
4. Creates matrix CSVs suitable for visualization
5. Outputs a clean daily table
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_CSV = Path("data_raw/all_daily_raw.csv")
OUT_DIR = Path("data_processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_and_clean_data():
    """Load raw data and perform initial cleaning."""
    print("Loading raw data...")
    df = pd.read_csv(RAW_CSV)

    print(f"  Total records: {len(df):,}")

    # Keep only TMAX and TMIN
    df = df[df["datatype"].isin(["TMAX", "TMIN"])]
    print(f"  Records after filtering to TMAX/TMIN: {len(df):,}")

    # Convert date column to datetime
    df["date"] = pd.to_datetime(df["date"])

    # NOAA metric units: value is in tenths of °C
    df["temp_c"] = df["value"] / 10.0
    df["temp_f"] = df["temp_c"] * 9.0 / 5.0 + 32.0

    # Extract date components
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["doy"] = df["date"].dt.dayofyear

    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Year range: {df['year'].min()} to {df['year'].max()}")

    return df


def remove_leap_days(df):
    """Remove February 29 to ensure all years have 365 days."""
    print("\nRemoving leap days (Feb 29)...")

    initial_count = len(df)
    is_leap_day = (df["month"] == 2) & (df["day"] == 29)
    df = df[~is_leap_day].copy()

    removed = initial_count - len(df)
    print(f"  Removed {removed} leap day records")

    # After removing Feb 29, we need to adjust DOY for dates after Feb 28 in leap years
    # to ensure consistency (all years map to 1-365)
    leap_years = df[df["date"].dt.is_leap_year]["year"].unique()

    for year in leap_years:
        # For leap years, shift DOY down by 1 for all dates after Feb 28
        mask = (df["year"] == year) & (df["month"] > 2)
        df.loc[mask, "doy"] = df.loc[mask, "doy"] - 1

    return df


def check_data_quality(df):
    """Check and report on data quality."""
    print("\nData quality check:")

    # Count records per year per data type
    yearly_counts = df.groupby(["year", "datatype"]).size().unstack(fill_value=0)

    print(f"\nRecords per year:")
    print(f"  Expected: 365 per data type")

    incomplete_years = []
    for year in yearly_counts.index:
        tmax_count = yearly_counts.loc[year, "TMAX"] if "TMAX" in yearly_counts.columns else 0
        tmin_count = yearly_counts.loc[year, "TMIN"] if "TMIN" in yearly_counts.columns else 0

        if tmax_count < 300 or tmin_count < 300:  # Significantly incomplete
            incomplete_years.append(year)
            print(f"  {year}: TMAX={tmax_count}, TMIN={tmin_count} (incomplete)")

    if incomplete_years:
        print(f"\nWarning: {len(incomplete_years)} year(s) have significant missing data")
    else:
        print("\nAll years have reasonably complete data")


def create_matrices(df):
    """Create pivot tables (matrices) for TMAX and TMIN."""
    print("\nCreating temperature matrices...")

    # Pivot to create matrices: rows = doy (1-365), columns = year
    tmax = df[df["datatype"] == "TMAX"].pivot_table(
        index="doy",
        columns="year",
        values="temp_f",
        aggfunc="first"  # Use first value if there are duplicates
    )

    tmin = df[df["datatype"] == "TMIN"].pivot_table(
        index="doy",
        columns="year",
        values="temp_f",
        aggfunc="first"
    )

    print(f"  TMAX matrix: {tmax.shape[0]} days × {tmax.shape[1]} years")
    print(f"  TMIN matrix: {tmin.shape[0]} days × {tmin.shape[1]} years")

    # Check for missing values
    tmax_missing = tmax.isna().sum().sum()
    tmin_missing = tmin.isna().sum().sum()

    print(f"  Missing TMAX values: {tmax_missing}")
    print(f"  Missing TMIN values: {tmin_missing}")

    return tmax, tmin


def save_outputs(df, tmax, tmin):
    """Save all processed data files."""
    print("\nSaving processed data...")

    # Save clean daily table
    daily_cols = ["date", "year", "month", "day", "doy", "datatype", "temp_f", "temp_c"]
    daily_file = OUT_DIR / "daily_clean.csv"
    df[daily_cols].to_csv(daily_file, index=False)
    print(f"  Saved daily data: {daily_file}")

    # Save matrices
    tmax_file = OUT_DIR / "tmax_matrix.csv"
    tmin_file = OUT_DIR / "tmin_matrix.csv"

    tmax.to_csv(tmax_file)
    tmin.to_csv(tmin_file)

    print(f"  Saved TMAX matrix: {tmax_file}")
    print(f"  Saved TMIN matrix: {tmin_file}")


def print_summary_stats(df):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("Summary Statistics")
    print("=" * 70)

    tmax_data = df[df["datatype"] == "TMAX"]["temp_f"]
    tmin_data = df[df["datatype"] == "TMIN"]["temp_f"]

    print("\nDaily High Temperatures (TMAX):")
    print(f"  Min: {tmax_data.min():.1f}°F")
    print(f"  Max: {tmax_data.max():.1f}°F")
    print(f"  Mean: {tmax_data.mean():.1f}°F")
    print(f"  Median: {tmax_data.median():.1f}°F")

    print("\nDaily Low Temperatures (TMIN):")
    print(f"  Min: {tmin_data.min():.1f}°F")
    print(f"  Max: {tmin_data.max():.1f}°F")
    print(f"  Mean: {tmin_data.mean():.1f}°F")
    print(f"  Median: {tmin_data.median():.1f}°F")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Temperature Data Normalization")
    print("=" * 70)

    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {RAW_CSV}\n"
            "Please run fetch_noaa.py first to download the data."
        )

    # Load and clean
    df = load_and_clean_data()

    # Remove leap days
    df = remove_leap_days(df)

    # Check quality
    check_data_quality(df)

    # Create matrices
    tmax, tmin = create_matrices(df)

    # Save outputs
    save_outputs(df, tmax, tmin)

    # Print stats
    print_summary_stats(df)

    print("\n" + "=" * 70)
    print("Normalization complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
