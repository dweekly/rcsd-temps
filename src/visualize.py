#!/usr/bin/env python3
"""
Generate visualization of Redwood City temperature extremes.

This script:
1. Loads processed temperature matrices
2. Creates a two-panel figure (TMAX and TMIN)
3. Plots all historical years in gray
4. Highlights the last 3 years in color
5. Saves high-resolution output
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import numpy as np

DATA_DIR = Path("data_processed")
OUT_DIR = Path("figures")
OUT_DIR.mkdir(exist_ok=True)

# Month start day-of-year values (for non-leap years)
MONTH_STARTS = {
    "Jan": 1, "Feb": 32, "Mar": 60, "Apr": 91, "May": 121, "Jun": 152,
    "Jul": 182, "Aug": 213, "Sep": 244, "Oct": 274, "Nov": 305, "Dec": 335
}


def load_matrices():
    """Load temperature matrices from CSV files."""
    print("Loading temperature matrices...")

    tmax_file = DATA_DIR / "tmax_matrix.csv"
    tmin_file = DATA_DIR / "tmin_matrix.csv"

    if not tmax_file.exists() or not tmin_file.exists():
        raise FileNotFoundError(
            f"Processed data files not found in {DATA_DIR}\n"
            "Please run normalize.py first to process the data."
        )

    tmax = pd.read_csv(tmax_file, index_col=0)
    tmin = pd.read_csv(tmin_file, index_col=0)

    # Convert column names (years) to integers
    tmax.columns = tmax.columns.astype(int)
    tmin.columns = tmin.columns.astype(int)

    print(f"  TMAX: {tmax.shape[0]} days × {tmax.shape[1]} years ({tmax.columns.min()}-{tmax.columns.max()})")
    print(f"  TMIN: {tmin.shape[0]} days × {tmin.shape[1]} years ({tmin.columns.min()}-{tmin.columns.max()})")

    return tmax, tmin


def plot_panel(ax, matrix, highlight_years, title, is_max=True):
    """
    Plot a single panel (either TMAX or TMIN).

    Args:
        ax: Matplotlib axis
        matrix: DataFrame with DOY as index, years as columns
        highlight_years: List of years to highlight
        title: Panel title
        is_max: True for TMAX, False for TMIN
    """
    doys = matrix.index.values
    years = sorted(matrix.columns)

    # Define colors for highlighted years (most recent is darkest/boldest)
    if is_max:
        # Reds/oranges for highs
        colors = ["#ffb347", "#ff7f50", "#d7301f"]
    else:
        # Blues for lows
        colors = ["#9ecae1", "#4292c6", "#08519c"]

    widths = [1.3, 1.7, 2.1]

    # Plot historical years (all except highlighted ones)
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

    # Plot highlighted years
    for i, yr in enumerate(highlight_years):
        if yr not in matrix.columns:
            continue

        color = colors[i]
        width = widths[i]

        ax.plot(
            doys,
            matrix[yr].values,
            color=color,
            linewidth=width,
            label=str(yr),
            zorder=2 + i,
        )

        # Add year label at the right edge
        valid_data = matrix[yr].dropna()
        if len(valid_data) > 0:
            y_last = valid_data.iloc[-1]
            x_last = valid_data.index[-1]
            ax.text(
                x_last + 3,
                y_last,
                str(yr),
                color=color,
                fontsize=10,
                fontweight="bold",
                va="center",
            )

    # Styling
    ax.set_ylabel("Temperature (°F)", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.grid(True, color="#eeeeee", linewidth=0.5, zorder=0)
    ax.set_xlim(1, 365)

    # Add legend for highlighted years
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)


def create_visualization(tmax, tmin, num_highlight=3):
    """
    Create the complete two-panel visualization.

    Args:
        tmax: TMAX matrix
        tmin: TMIN matrix
        num_highlight: Number of recent years to highlight
    """
    print(f"\nCreating visualization (highlighting last {num_highlight} years)...")

    years = sorted(tmax.columns)
    highlight_years = years[-num_highlight:]

    print(f"  Highlighting years: {highlight_years}")

    # Create figure with two panels
    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(14, 10),
        sharex=True,
        dpi=100  # Lower DPI for display, will increase for save
    )

    # Plot TMAX panel
    plot_panel(
        ax1,
        tmax,
        highlight_years,
        "Daily High Temperatures (TMAX)",
        is_max=True
    )

    # Plot TMIN panel
    plot_panel(
        ax2,
        tmin,
        highlight_years,
        "Daily Low Temperatures (TMIN)",
        is_max=False
    )

    # Set x-axis labels (months) on bottom panel only
    ax2.set_xticks(list(MONTH_STARTS.values()))
    ax2.set_xticklabels(list(MONTH_STARTS.keys()))
    ax2.set_xlabel("Month", fontsize=11)

    # Overall title
    fig.suptitle(
        f"Redwood City, CA Daily Temperature Extremes ({years[0]}–{years[-1]})\n"
        f"Each gray line represents one year; last {num_highlight} years highlighted in color",
        fontsize=14,
        fontweight="bold"
    )

    fig.tight_layout(rect=[0, 0.03, 1, 0.96])

    return fig


def save_figure(fig):
    """Save the figure in multiple formats."""
    print("\nSaving visualizations...")

    # High-resolution PNG
    png_file = OUT_DIR / "redwoodcity_temp_extremes.png"
    fig.savefig(png_file, dpi=500, bbox_inches="tight")
    print(f"  Saved PNG: {png_file}")

    # PDF (vector format, good for printing)
    pdf_file = OUT_DIR / "redwoodcity_temp_extremes.pdf"
    fig.savefig(pdf_file, bbox_inches="tight")
    print(f"  Saved PDF: {pdf_file}")

    # SVG (vector format, good for web)
    svg_file = OUT_DIR / "redwoodcity_temp_extremes.svg"
    fig.savefig(svg_file, bbox_inches="tight")
    print(f"  Saved SVG: {svg_file}")


def print_extremes(tmax, tmin):
    """Find and print record extremes."""
    print("\n" + "=" * 70)
    print("Record Extremes")
    print("=" * 70)

    # Find global max TMAX
    tmax_max = tmax.max().max()
    tmax_max_loc = tmax.stack().idxmax()
    print(f"\nRecord High Temperature: {tmax_max:.1f}°F")
    print(f"  Day {tmax_max_loc[0]} of {tmax_max_loc[1]}")

    # Find global min TMAX
    tmax_min = tmax.min().min()
    tmax_min_loc = tmax.stack().idxmin()
    print(f"\nColdest Daily High: {tmax_min:.1f}°F")
    print(f"  Day {tmax_min_loc[0]} of {tmax_min_loc[1]}")

    # Find global max TMIN
    tmin_max = tmin.max().max()
    tmin_max_loc = tmin.stack().idxmax()
    print(f"\nWarmest Daily Low: {tmin_max:.1f}°F")
    print(f"  Day {tmin_max_loc[0]} of {tmin_max_loc[1]}")

    # Find global min TMIN
    tmin_min = tmin.min().min()
    tmin_min_loc = tmin.stack().idxmin()
    print(f"\nRecord Low Temperature: {tmin_min:.1f}°F")
    print(f"  Day {tmin_min_loc[0]} of {tmin_min_loc[1]}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Temperature Visualization Generator")
    print("=" * 70)

    # Load data
    tmax, tmin = load_matrices()

    # Print extremes
    print_extremes(tmax, tmin)

    # Create visualization
    fig = create_visualization(tmax, tmin, num_highlight=3)

    # Save outputs
    save_figure(fig)

    print("\n" + "=" * 70)
    print("Visualization complete!")
    print("=" * 70)
    print(f"\nOutput files saved to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
