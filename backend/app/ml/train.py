#!/usr/bin/env python3
"""
Train the next-day spot price model from historical data across all five
sources (price, production, flow, reservoir, weather) and save it to
model.joblib.

Needs enough history to be useful: at least a few weeks of daily data per
zone so the time-based train/test split and lag features are meaningful.
Re-run this periodically (e.g. weekly, alongside the ingest scripts) to
keep the model current — it is not retrained automatically.

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

from .features import FEATURE_COLUMNS, TARGET_COLUMN, build_training_frame

MODEL_PATH = Path(__file__).parent / "model.joblib"
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


def main() -> int:
    warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")

    print("Building training frame from spot_price, production_per_source, "
          "cross_border_flow, reservoir_fill and weather_observation...")
    df = build_training_frame()

    if len(df) < MIN_TRAINING_ROWS:
        print(
            f"ERROR: only {len(df)} usable (zone, day) rows after feature engineering "
            f"(need at least {MIN_TRAINING_ROWS}). Run the ingest scripts for longer "
            f"before training — the model needs several weeks of daily history per zone.",
            file=sys.stderr,
        )
        return 1

    df["zone"] = df["zone"].astype("category")
    train_df, test_df = time_based_split(df)
    print(f"Training on {len(train_df)} rows ({df['day'].min()} to {train_df['day'].max()}), "
          f"holding out {len(test_df)} rows ({test_df['day'].min() if len(test_df) else '—'} to {df['day'].max()})")

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df[TARGET_COLUMN]

    model = HistGradientBoostingRegressor(categorical_features="from_dtype", random_state=42)
    model.fit(X_train, y_train)

    metrics = {}
    if len(test_df) > 0:
        preds = model.predict(X_test)
        metrics = {
            "mae_eur_mwh": float(mean_absolute_error(y_test, preds)),
            "rmse_eur_mwh": float(root_mean_squared_error(y_test, preds)),
            "r2": float(r2_score(y_test, preds)) if len(test_df) > 1 else None,
            "n_test": len(test_df),
        }
        print(f"Holdout metrics: MAE={metrics['mae_eur_mwh']:.2f} EUR/MWh, "
              f"RMSE={metrics['rmse_eur_mwh']:.2f} EUR/MWh, R2={metrics['r2']}")
    else:
        print("WARNING: no holdout rows (too little history for a time-based split) — "
              "metrics unavailable. Model is still saved, but treat predictions with caution "
              "until more data accumulates.")

    print("Computing permutation feature importance on the training set...")
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
        "metrics": metrics,
        "feature_importances": [{"feature": n, "importance": float(v)} for n, v in importances],
    }
    joblib.dump(artifact, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
