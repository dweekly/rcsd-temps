#!/usr/bin/env python3
"""
Analyze "feels like" temperature trends for San Carlos Airport / Redwood City area.

This script:
1. Loads ASOS daily data with "feels like" temperatures
2. Counts days with extreme "feels like" conditions
3. Analyzes trends over time (1990-present)
4. Compares "feels like" vs raw temperature trends
5. Generates visualizations
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy import stats

DATA_DIR = Path("data_raw")
PROCESSED_DIR = Path("data_processed")
OUT_DIR = Path("figures")
OUT_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)


def load_asos_daily_data():
    """Load daily ASOS statistics."""
    print("Loading ASOS daily data...")

    daily_file = DATA_DIR / "asos_sql_daily.csv"
    if not daily_file.exists():
        raise FileNotFoundError(
            f"ASOS daily data not found: {daily_file}\n"
            "Please run fetch_feels_like.py first to download the data."
        )

    df = pd.read_csv(daily_file)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    print(f"  Loaded {len(df):,} days")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    return df


def calculate_extreme_days(df):
    """
    Calculate days with extreme "feels like" temperatures.

    Returns:
        DataFrame with yearly counts
    """
    print("\nCalculating extreme 'feels like' days per year...")

    # Define extreme conditions
    df["feels_hot_90"] = df["feel_max"] >= 90
    df["feels_hot_100"] = df["feel_max"] >= 100
    df["feels_cold_32"] = df["feel_min"] <= 32

    # Also track raw temperature for comparison
    df["raw_hot_90"] = df["tmpf_max"] >= 90
    df["raw_hot_100"] = df["tmpf_max"] >= 100

    # Determine school year (Aug-Jun)
    df["is_school_year"] = (
        ((df["month"] >= 8) & (df["month"] <= 12)) |
        ((df["month"] >= 1) & (df["month"] <= 6))
    )

    # Group by year
    yearly_stats = df.groupby("year").agg({
        # Feels like extremes
        "feels_hot_90": "sum",
        "feels_hot_100": "sum",
        "feels_cold_32": "sum",
        # Raw temperature extremes
        "raw_hot_90": "sum",
        "raw_hot_100": "sum",
    }).rename(columns={
        "feels_hot_90": "days_feels_above_90",
        "feels_hot_100": "days_feels_above_100",
        "feels_cold_32": "days_feels_below_32",
        "raw_hot_90": "days_temp_above_90",
        "raw_hot_100": "days_temp_above_100",
    })

    # Calculate school year stats
    school_df = df[df["is_school_year"]]
    school_stats = school_df.groupby("year").agg({
        "feels_hot_90": "sum",
        "raw_hot_90": "sum",
    }).rename(columns={
        "feels_hot_90": "school_days_feels_above_90",
        "raw_hot_90": "school_days_temp_above_90",
    })

    # Combine
    result = yearly_stats.join(school_stats, how="outer").fillna(0).astype(int)

    # Filter to years with reasonable data (at least 300 days)
    days_per_year = df.groupby("year").size()
    valid_years = days_per_year[days_per_year >= 300].index
    result = result.loc[valid_years]

    print(f"  Analyzed {len(result)} years with sufficient data")

    return result


def calculate_trend(x, y):
    """Calculate linear trend and return slope, intercept, r_value, p_value."""
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, intercept, r_value, p_value


def create_feels_like_visualization(extreme_days_df):
    """Create visualization comparing feels-like vs raw temperature trends."""
    print("\nCreating 'feels like' trend visualization...")

    years = extreme_days_df.index.values

    # Calculate trends
    slope_feels_90, intercept_feels_90, r_feels_90, p_feels_90 = calculate_trend(
        years, extreme_days_df["days_feels_above_90"]
    )
    slope_temp_90, intercept_temp_90, r_temp_90, p_temp_90 = calculate_trend(
        years, extreme_days_df["days_temp_above_90"]
    )

    slope_feels_100, intercept_feels_100, r_feels_100, p_feels_100 = calculate_trend(
        years, extreme_days_df["days_feels_above_100"]
    )
    slope_temp_100, intercept_temp_100, r_temp_100, p_temp_100 = calculate_trend(
        years, extreme_days_df["days_temp_above_100"]
    )

    # Create figure with 3 panels
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), dpi=100)

    # Panel 1: Days with feels-like temp >90°F
    ax1.scatter(years, extreme_days_df["days_feels_above_90"],
               alpha=0.6, s=40, color="#d7301f", label="'Feels Like' Temperature", zorder=3)
    ax1.scatter(years, extreme_days_df["days_temp_above_90"],
               alpha=0.4, s=30, color="#999999", label="Raw Temperature", zorder=2)

    trend_feels_90 = slope_feels_90 * years + intercept_feels_90
    trend_temp_90 = slope_temp_90 * years + intercept_temp_90

    ax1.plot(years, trend_feels_90, 'r-', linewidth=2,
            label=f"'Feels Like' Trend: {slope_feels_90:.3f} days/yr (p={p_feels_90:.3f})")
    ax1.plot(years, trend_temp_90, color='#666666', linewidth=2, linestyle='--',
            label=f"Raw Temp Trend: {slope_temp_90:.3f} days/yr (p={p_temp_90:.3f})")

    ax1.set_ylabel("Days Per Year", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"Days with Temperature ≥90°F: 'Feels Like' vs Raw Temperature\n"
        f"San Carlos Airport ({years[0]}-{years[-1]})",
        fontsize=12,
        fontweight="bold"
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left", fontsize=9)

    # Panel 2: Days with feels-like temp >100°F
    ax2.scatter(years, extreme_days_df["days_feels_above_100"],
               alpha=0.6, s=40, color="#7f0000", label="'Feels Like' Temperature", zorder=3)
    ax2.scatter(years, extreme_days_df["days_temp_above_100"],
               alpha=0.4, s=30, color="#999999", label="Raw Temperature", zorder=2)

    trend_feels_100 = slope_feels_100 * years + intercept_feels_100
    trend_temp_100 = slope_temp_100 * years + intercept_temp_100

    ax2.plot(years, trend_feels_100, color='#7f0000', linewidth=2,
            label=f"'Feels Like' Trend: {slope_feels_100:.3f} days/yr (p={p_feels_100:.3f})")
    ax2.plot(years, trend_temp_100, color='#666666', linewidth=2, linestyle='--',
            label=f"Raw Temp Trend: {slope_temp_100:.3f} days/yr (p={p_temp_100:.3f})")

    ax2.set_ylabel("Days Per Year", fontsize=11, fontweight="bold")
    ax2.set_title(
        "Days with Temperature ≥100°F: 'Feels Like' vs Raw Temperature",
        fontsize=12,
        fontweight="bold"
    )
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", fontsize=9)

    # Panel 3: School year comparison (feels-like only)
    ax3.scatter(years, extreme_days_df["school_days_feels_above_90"],
               alpha=0.6, s=40, color="#ff7f00", label="School Year (Aug-Jun)", zorder=3)
    ax3.scatter(years, extreme_days_df["days_feels_above_90"],
               alpha=0.4, s=30, color="#cccccc", label="Full Year", zorder=2)

    slope_school, intercept_school, r_school, p_school = calculate_trend(
        years, extreme_days_df["school_days_feels_above_90"]
    )
    trend_school = slope_school * years + intercept_school

    ax3.plot(years, trend_school, color='#d7301f', linewidth=2,
            label=f"School Year Trend: {slope_school:.3f} days/yr (p={p_school:.3f})")

    ax3.set_xlabel("Year", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Days Per Year", fontsize=11, fontweight="bold")
    ax3.set_title(
        "School Year vs Full Year: Days 'Feels Like' ≥90°F",
        fontsize=12,
        fontweight="bold"
    )
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left", fontsize=9)

    # Overall title
    fig.suptitle(
        "'Feels Like' Temperature Trends: San Carlos Airport / Redwood City Area\n"
        "Accounts for Humidity and Wind Effects",
        fontsize=14,
        fontweight="bold",
        y=0.995
    )

    fig.tight_layout(rect=[0, 0.03, 1, 0.99])

    return fig, {
        "slope_feels_90": slope_feels_90,
        "slope_temp_90": slope_temp_90,
        "slope_feels_100": slope_feels_100,
        "slope_temp_100": slope_temp_100,
        "slope_school": slope_school,
        "p_feels_90": p_feels_90,
        "p_temp_90": p_temp_90,
        "p_feels_100": p_feels_100,
        "p_temp_100": p_temp_100,
        "p_school": p_school,
    }


def print_summary_statistics(extreme_days_df, trends):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("'FEELS LIKE' TEMPERATURE TREND ANALYSIS SUMMARY")
    print("=" * 70)

    years = extreme_days_df.index
    recent_decade = extreme_days_df[extreme_days_df.index >= years[-1] - 10]
    early_period = extreme_days_df[extreme_days_df.index <= years[0] + 10]

    print("\nDays 'Feels Like' Above 90°F:")
    print(f"  Early period average ({years[0]}-{years[0]+10}): {early_period['days_feels_above_90'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['days_feels_above_90'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_feels_90']:.3f} days/year (p={trends['p_feels_90']:.4f})")

    print("\nDays Raw Temperature Above 90°F (for comparison):")
    print(f"  Early period average: {early_period['days_temp_above_90'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['days_temp_above_90'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_temp_90']:.3f} days/year (p={trends['p_temp_90']:.4f})")

    print("\nDays 'Feels Like' Above 100°F:")
    print(f"  Early period average: {early_period['days_feels_above_100'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['days_feels_above_100'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_feels_100']:.3f} days/year (p={trends['p_feels_100']:.4f})")

    print("\nSchool Year 'Feels Like' Days Above 90°F:")
    print(f"  Early period average: {early_period['school_days_feels_above_90'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['school_days_feels_above_90'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_school']:.3f} days/year (p={trends['p_school']:.4f})")


def save_data(extreme_days_df):
    """Save processed data."""
    output_file = PROCESSED_DIR / "feels_like_days_by_year.csv"
    extreme_days_df.to_csv(output_file)
    print(f"\n  Saved 'feels like' data: {output_file}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("'Feels Like' Temperature Trend Analysis")
    print("San Carlos Airport / Redwood City Area")
    print("=" * 70)

    # Load data
    df = load_asos_daily_data()

    # Calculate extreme days
    extreme_days_df = calculate_extreme_days(df)

    # Create visualization
    fig, trends = create_feels_like_visualization(extreme_days_df)

    # Save outputs
    print("\nSaving visualizations...")
    png_file = OUT_DIR / "feels_like_trends.png"
    pdf_file = OUT_DIR / "feels_like_trends.pdf"
    svg_file = OUT_DIR / "feels_like_trends.svg"

    fig.savefig(png_file, dpi=400, bbox_inches="tight")
    fig.savefig(pdf_file, bbox_inches="tight")
    fig.savefig(svg_file, bbox_inches="tight")

    print(f"  Saved PNG: {png_file}")
    print(f"  Saved PDF: {pdf_file}")
    print(f"  Saved SVG: {svg_file}")

    # Save data
    save_data(extreme_days_df)

    # Print summary
    print_summary_statistics(extreme_days_df, trends)

    print("\n" + "=" * 70)
    print("'Feels like' analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
