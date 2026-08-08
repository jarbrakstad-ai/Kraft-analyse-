#!/usr/bin/env python3
"""
Train the next-day price and supply/demand-balance models from historical
data across all six sources (price, production, consumption, flow,
reservoir, weather), saving them to model.joblib and deficit_model.joblib.

Needs enough history to be useful: at least a few weeks of daily data per
zone so the time-based train/test split and lag features are meaningful.
Re-run this periodically (e.g. weekly, alongside the ingest scripts) to
keep the models current — they are not retrained automatically.

The deficit model needs consumption data (see fetch_consumption.py) on
top of everything the price model needs — if there isn't enough of it
yet, that model is skipped with a warning rather than failing the whole
run, so the price model still gets (re)trained.

Usage (from backend/, with the venv active):
    python -m app.ml.train
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from .features import FEATURE_COLUMNS, TARGET_DEFICIT_COLUMN, TARGET_PRICE_COLUMN, build_training_frame

MODEL_PATH = Path(__file__).parent / "model.joblib"
DEFICIT_MODEL_PATH = Path(__file__).parent / "deficit_model.joblib"
MIN_TRAINING_ROWS = 20
TEST_FRACTION = 0.2


def time_based_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out the most recent TEST_FRACTION of *days* (not rows) as test data."""
    unique_days = sorted(df["day"].unique())
    split_index = max(1, int(len(unique_days) * (1 - TEST_FRACTION)))
    train_days = set(unique_days[:split_index])
    train_df = df[df["day"].isin(train_days)]
    test_df = df[~df["day"].isin(train_days)]
    return train_df, test_df


def train_one(df: pd.DataFrame, target_column: str, model_path: Path, metric_unit: str, label: str) -> bool:
    """Trains and saves one model for the given target column. Returns False (skips) if too little data."""
    usable = df.dropna(subset=[target_column])
    if len(usable) < MIN_TRAINING_ROWS:
        print(
            f"SKIPPING {label} model: only {len(usable)} usable rows for target '{target_column}' "
            f"(need at least {MIN_TRAINING_ROWS}). Run the relevant ingest script for longer first.",
            file=sys.stderr,
        )
        return False

    train_df, test_df = time_based_split(usable)
    print(f"[{label}] Training on {len(train_df)} rows ({usable['day'].min()} to {train_df['day'].max()}), "
          f"holding out {len(test_df)} rows ({test_df['day'].min() if len(test_df) else '—'} to {usable['day'].max()})")

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df[target_column]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df[target_column]

    model = HistGradientBoostingRegressor(categorical_features="from_dtype", random_state=42)
    model.fit(X_train, y_train)

    metrics = {}
    if len(test_df) > 0:
        preds = model.predict(X_test)
        metrics = {
            "mae": float(mean_absolute_error(y_test, preds)),
            "rmse": float(root_mean_squared_error(y_test, preds)),
            "r2": float(r2_score(y_test, preds)) if len(test_df) > 1 else None,
            "n_test": len(test_df),
        }
        print(f"[{label}] Holdout metrics: MAE={metrics['mae']:.2f} {metric_unit}, "
              f"RMSE={metrics['rmse']:.2f} {metric_unit}, R2={metrics['r2']}")
    else:
        print(f"[{label}] WARNING: no holdout rows (too little history for a time-based split) — "
              f"metrics unavailable. Model is still saved, but treat predictions with caution "
              f"until more data accumulates.")

    print(f"[{label}] Computing permutation feature importance on the training set...")
    imp = permutation_importance(model, X_train, y_train, n_repeats=5, random_state=42, n_jobs=-1)
    importances = sorted(zip(FEATURE_COLUMNS, imp.importances_mean), key=lambda x: -x[1])
    for name, value in importances[:8]:
        print(f"  {name}: {value:.3f}")

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "zone_categories": list(df["zone"].cat.categories),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_training_rows": len(train_df),
        "metric_unit": metric_unit,
        "metrics": metrics,
        "feature_importances": [{"feature": n, "importance": float(v)} for n, v in importances],
    }
    joblib.dump(artifact, model_path)
    print(f"[{label}] Saved model to {model_path}")
    return True


def main() -> int:
    warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")

    print("Building training frame from spot_price, production_per_source, consumption, "
          "cross_border_flow, reservoir_fill and weather_observation...")
    df = build_training_frame()

    if len(df) < MIN_TRAINING_ROWS:
        print(
            f"ERROR: only {len(df)} usable (zone, day) rows after feature engineering "
            f"(need at least {MIN_TRAINING_ROWS}). Run the ingest scripts for longer "
            f"before training — the models need several weeks of daily history per zone.",
            file=sys.stderr,
        )
        return 1

    df["zone"] = df["zone"].astype("category")

    price_ok = train_one(df, TARGET_PRICE_COLUMN, MODEL_PATH, "EUR/MWh", "price")
    print()
    deficit_ok = train_one(df, TARGET_DEFICIT_COLUMN, DEFICIT_MODEL_PATH, "MW", "deficit")

    if not price_ok and not deficit_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
