from __future__ import annotations

import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .features import FEATURE_COLUMNS, build_prediction_frame
from .train import MODEL_PATH

_artifact: dict[str, Any] | None = None
_artifact_mtime: float | None = None


class ModelNotTrainedError(RuntimeError):
    pass


class NoRecentDataError(RuntimeError):
    pass


def _load_artifact() -> dict[str, Any]:
    """Loads model.joblib, reloading if the file has changed since last load (e.g. after a re-train)."""
    global _artifact, _artifact_mtime

    if not MODEL_PATH.exists():
        raise ModelNotTrainedError(
            f"No trained model found at {MODEL_PATH}. Run 'python -m app.ml.train' from the backend/ "
            f"directory once there is enough historical data in the database."
        )

    mtime = MODEL_PATH.stat().st_mtime
    if _artifact is None or _artifact_mtime != mtime:
        _artifact = joblib.load(MODEL_PATH)
        _artifact_mtime = mtime
    return _artifact


def get_model_info() -> dict[str, Any]:
    artifact = _load_artifact()
    return {
        "trained_at": artifact["trained_at"],
        "n_training_rows": artifact["n_training_rows"],
        "metrics": artifact["metrics"],
        "feature_importances": artifact["feature_importances"],
        "zone_categories": artifact["zone_categories"],
    }


def predict_next_day_price(zone: str) -> dict[str, Any]:
    artifact = _load_artifact()
    model = artifact["model"]

    if zone not in artifact["zone_categories"]:
        raise NoRecentDataError(
            f"Zone '{zone}' was not present in the training data ({artifact['zone_categories']}). "
            f"The model can't make predictions for a zone it has never seen."
        )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")
        frame = build_prediction_frame(zone)

    if frame.empty:
        raise NoRecentDataError(f"No recent price data for zone '{zone}' to build a prediction from.")

    based_on_day: date = pd.Timestamp(frame["day"].iloc[0]).date()
    X = frame[FEATURE_COLUMNS].copy()
    X["zone"] = X["zone"].astype("category").cat.set_categories(artifact["zone_categories"])

    predicted_price = float(model.predict(X)[0])
    missing_features = [col for col in FEATURE_COLUMNS if col != "zone" and bool(X[col].isna().iloc[0])]

    return {
        "zone": zone,
        "based_on_day": based_on_day,
        "predicted_date": based_on_day + timedelta(days=1),
        "predicted_avg_price_eur_mwh": predicted_price,
        "missing_features": missing_features,
        "model_trained_at": artifact["trained_at"],
    }
