#!/usr/bin/env python3
"""
Analyze heat trends in Redwood City temperature data.

This script:
1. Counts days above 90°F and 100°F per year
2. Analyzes trends over time
3. Compares school year (Aug-Jun) vs full year
4. Generates visualizations showing climate change impact on education
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy import stats

DATA_DIR = Path("data_processed")
OUT_DIR = Path("figures")
OUT_DIR.mkdir(exist_ok=True)


def load_daily_data():
    """Load the clean daily temperature data."""
    print("Loading daily temperature data...")

    daily_file = DATA_DIR / "daily_clean.csv"
    if not daily_file.exists():
        raise FileNotFoundError(
            f"Daily data file not found: {daily_file}\n"
            "Please run normalize.py first to process the data."
        )

    df = pd.read_csv(daily_file)
    df["date"] = pd.to_datetime(df["date"])

    print(f"  Loaded {len(df):,} records")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    return df


def calculate_heat_days_per_year(df):
    """
    Calculate the number of days above temperature thresholds per year.

    Returns:
        DataFrame with columns: year, days_above_90, days_above_100,
                               school_days_above_90, school_days_above_100
    """
    print("\nCalculating heat days per year...")

    # Filter to TMAX only
    tmax_df = df[df["datatype"] == "TMAX"].copy()

    # Determine if date is in school year (Aug-June)
    # School year runs from Aug 15 to Jun 15 approximately
    tmax_df["is_school_year"] = (
        ((tmax_df["month"] >= 8) & (tmax_df["month"] <= 12)) |
        ((tmax_df["month"] >= 1) & (tmax_df["month"] <= 6))
    )

    # Count days above thresholds
    tmax_df["above_90"] = tmax_df["temp_f"] >= 90
    tmax_df["above_100"] = tmax_df["temp_f"] >= 100

    # Group by year
    yearly_stats = tmax_df.groupby("year").agg({
        "above_90": "sum",
        "above_100": "sum",
    }).rename(columns={
        "above_90": "days_above_90",
        "above_100": "days_above_100"
    })

    # Calculate school year stats
    school_stats = tmax_df[tmax_df["is_school_year"]].groupby("year").agg({
        "above_90": "sum",
        "above_100": "sum",
    }).rename(columns={
        "above_90": "school_days_above_90",
        "above_100": "school_days_above_100"
    })

    # Combine
    result = yearly_stats.join(school_stats, how="outer").fillna(0)
    result = result.astype(int)

    # Filter to years with reasonable data (at least 300 days)
    tmax_counts = tmax_df.groupby("year").size()
    valid_years = tmax_counts[tmax_counts >= 300].index
    result = result.loc[valid_years]

    print(f"  Analyzed {len(result)} years with sufficient data")

    return result


def calculate_trend(x, y):
    """Calculate linear trend and return slope, intercept, r_value, p_value."""
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, intercept, r_value, p_value


def create_heat_trend_visualization(heat_days_df):
    """Create comprehensive heat days trend visualization."""
    print("\nCreating heat trend visualization...")

    years = heat_days_df.index.values

    # Calculate trends
    slope_90, intercept_90, r_90, p_90 = calculate_trend(years, heat_days_df["days_above_90"])
    slope_100, intercept_100, r_100, p_100 = calculate_trend(years, heat_days_df["days_above_100"])
    slope_school, intercept_school, r_school, p_school = calculate_trend(
        years, heat_days_df["school_days_above_90"]
    )

    # Create figure with 3 panels
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), dpi=100)

    # Panel 1: Days above 90°F
    ax1.scatter(years, heat_days_df["days_above_90"], alpha=0.6, s=30, color="#d7301f")
    trend_90 = slope_90 * years + intercept_90
    ax1.plot(years, trend_90, 'r-', linewidth=2, label=f'Trend: {slope_90:.2f} days/year')

    ax1.set_ylabel("Days Above 90°F", fontsize=12, fontweight="bold")
    ax1.set_title(
        f"Days Above 90°F Per Year (1948-{years[-1]})\n"
        f"Trend: {slope_90:.3f} days/year (p={p_90:.4f})",
        fontsize=13,
        fontweight="bold"
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left", fontsize=10)

    # Add decade averages as bars in background
    decades = list(range(1950, 2030, 10))
    decade_avgs_90 = []
    decade_labels = []
    for decade_start in decades:
        decade_data = heat_days_df[
            (heat_days_df.index >= decade_start) &
            (heat_days_df.index < decade_start + 10)
        ]["days_above_90"]
        if len(decade_data) > 0:
            decade_avgs_90.append(decade_data.mean())
            decade_labels.append(f"{decade_start}s")

    # Panel 2: Days above 100°F
    ax2.scatter(years, heat_days_df["days_above_100"], alpha=0.6, s=30, color="#b30000")
    trend_100 = slope_100 * years + intercept_100
    ax2.plot(years, trend_100, color='#7f0000', linewidth=2, label=f'Trend: {slope_100:.2f} days/year')

    ax2.set_ylabel("Days Above 100°F", fontsize=12, fontweight="bold")
    ax2.set_title(
        f"Days Above 100°F Per Year (1948-{years[-1]})\n"
        f"Trend: {slope_100:.3f} days/year (p={p_100:.4f})",
        fontsize=13,
        fontweight="bold"
    )
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", fontsize=10)

    # Panel 3: School year comparison
    ax3.scatter(years, heat_days_df["school_days_above_90"],
               alpha=0.6, s=30, color="#ff7f00", label="School Year (Aug-Jun)")
    ax3.scatter(years, heat_days_df["days_above_90"],
               alpha=0.4, s=20, color="#cccccc", label="Full Year")

    trend_school = slope_school * years + intercept_school
    ax3.plot(years, trend_school, color='#d7301f', linewidth=2,
            label=f'School Year Trend: {slope_school:.2f} days/year')

    ax3.set_xlabel("Year", fontsize=12, fontweight="bold")
    ax3.set_ylabel("Days Above 90°F", fontsize=12, fontweight="bold")
    ax3.set_title(
        f"School Year vs Full Year: Days Above 90°F\n"
        f"School Year Trend: {slope_school:.3f} days/year (p={p_school:.4f})",
        fontsize=13,
        fontweight="bold"
    )
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left", fontsize=10)

    # Overall title
    fig.suptitle(
        "Redwood City Heat Trends: Climate Impact on Education (1948-2025)",
        fontsize=15,
        fontweight="bold",
        y=0.995
    )

    fig.tight_layout(rect=[0, 0.03, 1, 0.99])

    return fig, {
        "slope_90": slope_90,
        "slope_100": slope_100,
        "slope_school": slope_school,
        "r_90": r_90,
        "r_100": r_100,
        "r_school": r_school,
        "p_90": p_90,
        "p_100": p_100,
        "p_school": p_school
    }


def print_summary_statistics(heat_days_df, trends):
    """Print summary statistics about heat trends."""
    print("\n" + "=" * 70)
    print("HEAT TREND ANALYSIS SUMMARY")
    print("=" * 70)

    years = heat_days_df.index
    recent_decade = heat_days_df[heat_days_df.index >= years[-1] - 10]
    early_period = heat_days_df[heat_days_df.index <= 1970]

    print("\nDays Above 90°F:")
    print(f"  Historical average (1948-1970): {early_period['days_above_90'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['days_above_90'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_90']:.3f} days/year (p={trends['p_90']:.4f})")
    print(f"  Total increase: {trends['slope_90'] * (years[-1] - years[0]):.1f} days over {years[-1] - years[0]} years")

    print("\nDays Above 100°F:")
    print(f"  Historical average (1948-1970): {early_period['days_above_100'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['days_above_100'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_100']:.3f} days/year (p={trends['p_100']:.4f})")

    print("\nSchool Year Heat (Aug-Jun):")
    print(f"  Historical average (1948-1970): {early_period['school_days_above_90'].mean():.1f} days/year")
    print(f"  Recent decade average: {recent_decade['school_days_above_90'].mean():.1f} days/year")
    print(f"  Trend: {trends['slope_school']:.3f} days/year (p={trends['p_school']:.4f})")

    # Calculate years with extreme heat
    extreme_years_90 = heat_days_df[heat_days_df["days_above_90"] >= 20]
    extreme_years_100 = heat_days_df[heat_days_df["days_above_100"] >= 5]

    print("\nExtreme Heat Years:")
    print(f"  Years with 20+ days above 90°F: {len(extreme_years_90)}")
    print(f"  Years with 5+ days above 100°F: {len(extreme_years_100)}")

    if len(extreme_years_90) > 0:
        print(f"  Most recent: {extreme_years_90.index[-1]} ({extreme_years_90.iloc[-1]['days_above_90']} days >90°F)")


def save_heat_data(heat_days_df):
    """Save heat days data for further analysis."""
    output_file = DATA_DIR / "heat_days_by_year.csv"
    heat_days_df.to_csv(output_file)
    print(f"\n  Saved heat days data: {output_file}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Heat Trend Analysis for Redwood City, CA")
    print("=" * 70)

    # Load data
    df = load_daily_data()

    # Calculate heat days per year
    heat_days_df = calculate_heat_days_per_year(df)

    # Create visualization
    fig, trends = create_heat_trend_visualization(heat_days_df)

    # Save outputs
    print("\nSaving visualizations...")
    png_file = OUT_DIR / "heat_days_trend.png"
    pdf_file = OUT_DIR / "heat_days_trend.pdf"
    svg_file = OUT_DIR / "heat_days_trend.svg"

    fig.savefig(png_file, dpi=400, bbox_inches="tight")
    fig.savefig(pdf_file, bbox_inches="tight")
    fig.savefig(svg_file, bbox_inches="tight")

    print(f"  Saved PNG: {png_file}")
    print(f"  Saved PDF: {pdf_file}")
    print(f"  Saved SVG: {svg_file}")

    # Save data
    save_heat_data(heat_days_df)

    # Print summary
    print_summary_statistics(heat_days_df, trends)

    print("\n" + "=" * 70)
    print("Heat trend analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
