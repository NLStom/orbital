#!/usr/bin/env python3
"""
Prepare demo data for the "Missing Data Discovery" hackathon demo.

Downloads housing-related datasets from public sources:
1. Zillow ZHVI (home values) — monthly home values by metro
2. Zillow ZORI (rents) — monthly rents by metro
3. FRED UNRATE (unemployment) — monthly unemployment rate
4. FRED MORTGAGE30US (mortgage rates) — weekly 30yr fixed rate, resampled to monthly

Output: data/demo/ (~2MB total)

Usage:
    cd .
    python scripts/prepare_demo_data.py
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Zillow public data CSVs
ZHVI_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)
ZORI_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/"
    "Metro_zori_uc_sfrcondomfr_sm_sa_month.csv"
)

# FRED data CSVs
FRED_UNRATE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE"
FRED_MORTGAGE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"

# Filters
START_YEAR = 2015
END_YEAR = 2024
TOP_N_METROS = 50

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"
OUTPUT_DIR_AGG = Path(__file__).resolve().parent.parent / "data" / "demo-aggregated"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def download_csv(url: str, name: str) -> pd.DataFrame:
    """Download a CSV from a URL into a DataFrame."""
    try:
        import urllib.request

        print(f"  Downloading {name}...")
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        return pd.read_csv(io.BytesIO(data))
    except Exception as exc:
        print(f"  ERROR downloading {name}: {exc}")
        print(f"  URL: {url}")
        print(f"  You can manually download the file and place it in {OUTPUT_DIR}/")
        raise SystemExit(1)


def process_zillow_wide_to_long(
    df: pd.DataFrame, value_name: str, id_col: str = "RegionName"
) -> pd.DataFrame:
    """
    Pivot Zillow wide-format data to long format.
    Zillow CSVs have columns like: RegionID, SizeRank, RegionName, ..., 2015-01-31, 2015-02-28, ...
    """
    # Identify date columns (YYYY-MM-DD pattern)
    date_cols = [c for c in df.columns if len(c) == 10 and c[4] == "-"]

    # Filter to top metros by SizeRank
    if "SizeRank" in df.columns:
        df = df.nsmallest(TOP_N_METROS, "SizeRank")

    # Melt to long format
    long = df.melt(
        id_vars=[id_col],
        value_vars=date_cols,
        var_name="date",
        value_name=value_name,
    )
    long["date"] = pd.to_datetime(long["date"])
    long = long.rename(columns={id_col: "metro"})

    # Filter date range
    long = long[
        (long["date"].dt.year >= START_YEAR) & (long["date"].dt.year <= END_YEAR)
    ]

    # Drop NaN values
    long = long.dropna(subset=[value_name])

    return long.sort_values(["metro", "date"]).reset_index(drop=True)


def process_fred_monthly(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Process FRED data: parse dates, filter range, rename."""
    # FRED CSVs have observation_date (or DATE) and the value column
    date_col = "observation_date" if "observation_date" in df.columns else "DATE"
    val_col = [c for c in df.columns if c != date_col][0]

    result = pd.DataFrame()
    result["date"] = pd.to_datetime(df[date_col])
    result[value_col] = pd.to_numeric(df[val_col], errors="coerce")

    # Filter date range
    result = result[
        (result["date"].dt.year >= START_YEAR) & (result["date"].dt.year <= END_YEAR)
    ]

    return result.dropna().sort_values("date").reset_index(drop=True)


def process_fred_weekly_to_monthly(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Process FRED weekly data: resample to monthly averages."""
    date_col = "observation_date" if "observation_date" in df.columns else "DATE"
    val_col = [c for c in df.columns if c != date_col][0]

    temp = pd.DataFrame()
    temp["date"] = pd.to_datetime(df[date_col])
    temp[value_col] = pd.to_numeric(df[val_col], errors="coerce")

    # Filter date range
    temp = temp[
        (temp["date"].dt.year >= START_YEAR) & (temp["date"].dt.year <= END_YEAR)
    ]
    temp = temp.dropna()

    # Resample weekly -> monthly (average)
    temp = temp.set_index("date")
    monthly = temp.resample("MS").mean()  # MS = month start
    monthly = monthly.dropna().reset_index()

    return monthly.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Preparing demo data for Missing Data Discovery demo")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Home values (Zillow ZHVI)
    print("\n[1/4] Home values (Zillow ZHVI)")
    zhvi_raw = download_csv(ZHVI_URL, "ZHVI")
    home_values = process_zillow_wide_to_long(zhvi_raw, "home_value")
    out_path = OUTPUT_DIR / "home_values.csv"
    home_values.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(home_values)} rows, {out_path.stat().st_size / 1024:.0f} KB)")

    # 2. Rents (Zillow ZORI)
    print("\n[2/4] Rents (Zillow ZORI)")
    zori_raw = download_csv(ZORI_URL, "ZORI")
    rents = process_zillow_wide_to_long(zori_raw, "rent")
    out_path = OUTPUT_DIR / "rents.csv"
    rents.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(rents)} rows, {out_path.stat().st_size / 1024:.0f} KB)")

    # 3. Unemployment (FRED UNRATE)
    print("\n[3/4] Unemployment rate (FRED UNRATE)")
    unrate_raw = download_csv(FRED_UNRATE_URL, "UNRATE")
    economic = process_fred_monthly(unrate_raw, "unemployment_rate")
    out_path = OUTPUT_DIR / "economic.csv"
    economic.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(economic)} rows, {out_path.stat().st_size / 1024:.0f} KB)")

    # 4. Mortgage rates (FRED MORTGAGE30US) — THE WITHHELD DATASET
    print("\n[4/4] Mortgage rates (FRED MORTGAGE30US) — withheld for demo")
    mortgage_raw = download_csv(FRED_MORTGAGE_URL, "MORTGAGE30US")
    mortgage_rates = process_fred_weekly_to_monthly(mortgage_raw, "mortgage_rate")
    out_path = OUTPUT_DIR / "mortgage_rates.csv"
    mortgage_rates.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(mortgage_rates)} rows, {out_path.stat().st_size / 1024:.0f} KB)")

    # --- Aggregated variant (no metro column) ---
    print("\n" + "-" * 60)
    print("Creating aggregated variant (national average, no metro)")
    print("-" * 60)

    OUTPUT_DIR_AGG.mkdir(parents=True, exist_ok=True)

    # Home values → national monthly average
    home_values_agg = (
        home_values
        .groupby("date", as_index=False)["home_value"]
        .mean()
        .sort_values("date")
        .reset_index(drop=True)
    )
    out_path = OUTPUT_DIR_AGG / "home_values.csv"
    home_values_agg.to_csv(out_path, index=False)
    print(f"  Saved: {out_path} ({len(home_values_agg)} rows)")

    # Economic + mortgage rates are the same (already national)
    for fname in ("economic.csv", "mortgage_rates.csv"):
        src = OUTPUT_DIR / fname
        dst = OUTPUT_DIR_AGG / fname
        dst.write_bytes(src.read_bytes())
        print(f"  Copied: {dst}")

    # Summary
    print("\n" + "=" * 60)
    print("Demo data preparation complete!")
    print()
    print(f"  data/demo/            — per-metro (50 cities, {len(home_values)} rows)")
    print(f"  data/demo-aggregated/ — national average ({len(home_values_agg)} rows, no metro)")
    print()
    print("For the demo (aggregated version):")
    print("  1. Upload home_values.csv + economic.csv from data/demo-aggregated/")
    print("  2. Ask: 'What economic factors drive home prices? Build a model.'")
    print("  3. After it discovers missing patterns in residuals...")
    print("  4. Upload mortgage_rates.csv and say: 'Retrain with this new data'")
    print("=" * 60)


if __name__ == "__main__":
    main()
