#!/usr/bin/env python3
"""
Analyze humidity and wind trends for San Carlos Airport / Redwood City area.

This script:
1. Loads ASOS daily data with humidity and wind measurements
2. Analyzes long-term trends in these meteorological variables
3. Examines how humidity and wind patterns have changed over time
4. Generates visualizations showing trends (1990-present)
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


def calculate_yearly_averages(df):
    """
    Calculate yearly averages for humidity and wind.

    Returns:
        DataFrame with yearly statistics
    """
    print("\nCalculating yearly averages...")

    # Group by year
    yearly_stats = df.groupby("year").agg({
        "relh_mean": "mean",
        "relh_max": "mean",
        "relh_min": "mean",
        "sknt_mean": "mean",
        "sknt_max": "mean",
        "dwpf_mean": "mean",
    }).rename(columns={
        "relh_mean": "avg_humidity",
        "relh_max": "avg_max_humidity",
        "relh_min": "avg_min_humidity",
        "sknt_mean": "avg_wind_speed",
        "sknt_max": "avg_max_wind_speed",
        "dwpf_mean": "avg_dew_point",
    })

    # Calculate summer averages (Jun-Sep)
    summer_df = df[df["month"].isin([6, 7, 8, 9])]
    summer_stats = summer_df.groupby("year").agg({
        "relh_mean": "mean",
        "sknt_mean": "mean",
        "dwpf_mean": "mean",
    }).rename(columns={
        "relh_mean": "summer_humidity",
        "sknt_mean": "summer_wind_speed",
        "dwpf_mean": "summer_dew_point",
    })

    # Combine
    result = yearly_stats.join(summer_stats, how="outer")

    # Filter to years with reasonable data (at least 300 days)
    days_per_year = df.groupby("year").size()
    valid_years = days_per_year[days_per_year >= 300].index
    result = result.loc[valid_years]

    print(f"  Analyzed {len(result)} years with sufficient data")

    return result


def calculate_trend(x, y):
    """Calculate linear trend and return slope, intercept, r_value, p_value."""
    # Remove any NaN values
    mask = ~(np.isnan(x) | np.isnan(y))
    x_clean = x[mask]
    y_clean = y[mask]

    if len(x_clean) < 2:
        return 0, 0, 0, 1.0

    slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
    return slope, intercept, r_value, p_value


def create_humidity_wind_visualization(yearly_stats):
    """Create visualization of humidity and wind trends."""
    print("\nCreating humidity and wind trend visualization...")

    years = yearly_stats.index.values

    # Calculate trends
    slope_hum, intercept_hum, r_hum, p_hum = calculate_trend(
        years, yearly_stats["avg_humidity"]
    )
    slope_wind, intercept_wind, r_wind, p_wind = calculate_trend(
        years, yearly_stats["avg_wind_speed"]
    )
    slope_dew, intercept_dew, r_dew, p_dew = calculate_trend(
        years, yearly_stats["avg_dew_point"]
    )

    slope_sum_hum, intercept_sum_hum, r_sum_hum, p_sum_hum = calculate_trend(
        years, yearly_stats["summer_humidity"]
    )
    slope_sum_wind, intercept_sum_wind, r_sum_wind, p_sum_wind = calculate_trend(
        years, yearly_stats["summer_wind_speed"]
    )

    # Create figure with 4 panels
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12), dpi=100)

    # Panel 1: Average Relative Humidity
    ax1.scatter(years, yearly_stats["avg_humidity"],
               alpha=0.6, s=40, color="#2E86AB", label="Annual Average", zorder=3)

    trend_hum = slope_hum * years + intercept_hum
    ax1.plot(years, trend_hum, 'b-', linewidth=2,
            label=f"Trend: {slope_hum:.3f}%/yr (p={p_hum:.3f})")

    ax1.set_ylabel("Relative Humidity (%)", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"Annual Average Relative Humidity\n"
        f"San Carlos Airport ({years[0]}-{years[-1]})",
        fontsize=12,
        fontweight="bold"
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best", fontsize=9)
    ax1.set_ylim(bottom=0)

    # Panel 2: Average Wind Speed
    ax2.scatter(years, yearly_stats["avg_wind_speed"],
               alpha=0.6, s=40, color="#A23B72", label="Annual Average", zorder=3)

    trend_wind = slope_wind * years + intercept_wind
    ax2.plot(years, trend_wind, color="#A23B72", linewidth=2,
            label=f"Trend: {slope_wind:.3f} knots/yr (p={p_wind:.3f})")

    ax2.set_ylabel("Wind Speed (knots)", fontsize=11, fontweight="bold")
    ax2.set_title(
        "Annual Average Wind Speed",
        fontsize=12,
        fontweight="bold"
    )
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best", fontsize=9)
    ax2.set_ylim(bottom=0)

    # Panel 3: Summer Humidity vs Annual
    ax3.scatter(years, yearly_stats["summer_humidity"],
               alpha=0.6, s=40, color="#F18F01", label="Summer (Jun-Sep)", zorder=3)
    ax3.scatter(years, yearly_stats["avg_humidity"],
               alpha=0.3, s=30, color="#cccccc", label="Annual Average", zorder=2)

    trend_sum_hum = slope_sum_hum * years + intercept_sum_hum
    ax3.plot(years, trend_sum_hum, color="#F18F01", linewidth=2,
            label=f"Summer Trend: {slope_sum_hum:.3f}%/yr (p={p_sum_hum:.3f})")

    ax3.set_xlabel("Year", fontsize=11, fontweight="bold")
    ax3.set_ylabel("Relative Humidity (%)", fontsize=11, fontweight="bold")
    ax3.set_title(
        "Summer vs Annual Relative Humidity",
        fontsize=12,
        fontweight="bold"
    )
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="best", fontsize=9)
    ax3.set_ylim(bottom=0)

    # Panel 4: Average Dew Point
    ax4.scatter(years, yearly_stats["avg_dew_point"],
               alpha=0.6, s=40, color="#06A77D", label="Annual Average", zorder=3)

    trend_dew = slope_dew * years + intercept_dew
    ax4.plot(years, trend_dew, color="#06A77D", linewidth=2,
            label=f"Trend: {slope_dew:.3f}°F/yr (p={p_dew:.3f})")

    ax4.set_xlabel("Year", fontsize=11, fontweight="bold")
    ax4.set_ylabel("Dew Point (°F)", fontsize=11, fontweight="bold")
    ax4.set_title(
        "Annual Average Dew Point Temperature",
        fontsize=12,
        fontweight="bold"
    )
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc="best", fontsize=9)

    # Overall title
    fig.suptitle(
        "Humidity and Wind Trends: San Carlos Airport / Redwood City Area\n"
        "Factors Affecting 'Feels Like' Temperature",
        fontsize=14,
        fontweight="bold",
        y=0.995
    )

    fig.tight_layout(rect=[0, 0.03, 1, 0.99])

    return fig, {
        "slope_humidity": slope_hum,
        "slope_wind": slope_wind,
        "slope_dew_point": slope_dew,
        "slope_summer_humidity": slope_sum_hum,
        "slope_summer_wind": slope_sum_wind,
        "p_humidity": p_hum,
        "p_wind": p_wind,
        "p_dew_point": p_dew,
        "p_summer_humidity": p_sum_hum,
        "p_summer_wind": p_sum_wind,
    }


def print_summary_statistics(yearly_stats, trends):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("HUMIDITY AND WIND TREND ANALYSIS SUMMARY")
    print("=" * 70)

    years = yearly_stats.index
    recent_decade = yearly_stats[yearly_stats.index >= years[-1] - 10]
    early_period = yearly_stats[yearly_stats.index <= years[0] + 10]

    print("\nRelative Humidity:")
    print(f"  Early period average ({years[0]}-{years[0]+10}): {early_period['avg_humidity'].mean():.1f}%")
    print(f"  Recent decade average: {recent_decade['avg_humidity'].mean():.1f}%")
    print(f"  Trend: {trends['slope_humidity']:.3f}%/year (p={trends['p_humidity']:.4f})")

    print("\nSummer Relative Humidity (Jun-Sep):")
    print(f"  Early period average: {early_period['summer_humidity'].mean():.1f}%")
    print(f"  Recent decade average: {recent_decade['summer_humidity'].mean():.1f}%")
    print(f"  Trend: {trends['slope_summer_humidity']:.3f}%/year (p={trends['p_summer_humidity']:.4f})")

    print("\nWind Speed:")
    print(f"  Early period average: {early_period['avg_wind_speed'].mean():.1f} knots")
    print(f"  Recent decade average: {recent_decade['avg_wind_speed'].mean():.1f} knots")
    print(f"  Trend: {trends['slope_wind']:.3f} knots/year (p={trends['p_wind']:.4f})")

    print("\nDew Point Temperature:")
    print(f"  Early period average: {early_period['avg_dew_point'].mean():.1f}°F")
    print(f"  Recent decade average: {recent_decade['avg_dew_point'].mean():.1f}°F")
    print(f"  Trend: {trends['slope_dew_point']:.3f}°F/year (p={trends['p_dew_point']:.4f})")

    # Interpretation
    print("\n" + "=" * 70)
    print("INTERPRETATION")
    print("=" * 70)

    if abs(trends['slope_humidity']) < 0.1 and trends['p_humidity'] > 0.05:
        print("\n✓ Humidity: No significant trend detected")
    elif trends['slope_humidity'] > 0 and trends['p_humidity'] < 0.05:
        print(f"\n↑ Humidity: Significant INCREASE of {trends['slope_humidity']:.3f}%/year")
    elif trends['slope_humidity'] < 0 and trends['p_humidity'] < 0.05:
        print(f"\n↓ Humidity: Significant DECREASE of {abs(trends['slope_humidity']):.3f}%/year")

    if abs(trends['slope_wind']) < 0.05 and trends['p_wind'] > 0.05:
        print("✓ Wind Speed: No significant trend detected")
    elif trends['slope_wind'] > 0 and trends['p_wind'] < 0.05:
        print(f"↑ Wind Speed: Significant INCREASE of {trends['slope_wind']:.3f} knots/year")
    elif trends['slope_wind'] < 0 and trends['p_wind'] < 0.05:
        print(f"↓ Wind Speed: Significant DECREASE of {abs(trends['slope_wind']):.3f} knots/year")


def save_data(yearly_stats):
    """Save processed data."""
    output_file = PROCESSED_DIR / "humidity_wind_by_year.csv"
    yearly_stats.to_csv(output_file)
    print(f"\n  Saved humidity/wind data: {output_file}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Humidity and Wind Trend Analysis")
    print("San Carlos Airport / Redwood City Area")
    print("=" * 70)

    # Load data
    df = load_asos_daily_data()

    # Calculate yearly averages
    yearly_stats = calculate_yearly_averages(df)

    # Create visualization
    fig, trends = create_humidity_wind_visualization(yearly_stats)

    # Save outputs
    print("\nSaving visualizations...")
    png_file = OUT_DIR / "humidity_wind_trends.png"
    pdf_file = OUT_DIR / "humidity_wind_trends.pdf"
    svg_file = OUT_DIR / "humidity_wind_trends.svg"

    fig.savefig(png_file, dpi=400, bbox_inches="tight")
    fig.savefig(pdf_file, bbox_inches="tight")
    fig.savefig(svg_file, bbox_inches="tight")

    print(f"  Saved PNG: {png_file}")
    print(f"  Saved PDF: {pdf_file}")
    print(f"  Saved SVG: {svg_file}")

    # Save data
    save_data(yearly_stats)

    # Print summary
    print_summary_statistics(yearly_stats, trends)

    print("\n" + "=" * 70)
    print("Humidity and wind analysis complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
