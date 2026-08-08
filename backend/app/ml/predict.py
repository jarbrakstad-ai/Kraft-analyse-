from __future__ import annotations

import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .features import FEATURE_COLUMNS, build_prediction_frame
from .train import DEFICIT_MODEL_PATH, MODEL_PATH

_artifact_cache: dict[Path, tuple[float, dict[str, Any]]] = {}


class ModelNotTrainedError(RuntimeError):
    pass


class NoRecentDataError(RuntimeError):
    pass


def _load_artifact(model_path: Path) -> dict[str, Any]:
    """Loads a model.joblib artifact, reloading if the file has changed since last load (e.g. after a re-train)."""
    if not model_path.exists():
        raise ModelNotTrainedError(
            f"No trained model found at {model_path}. Run 'python -m app.ml.train' from the backend/ "
            f"directory once there is enough historical data in the database."
        )

    mtime = model_path.stat().st_mtime
    cached = _artifact_cache.get(model_path)
    if cached is None or cached[0] != mtime:
        artifact = joblib.load(model_path)
        _artifact_cache[model_path] = (mtime, artifact)
        return artifact
    return cached[1]


def _model_info(model_path: Path) -> dict[str, Any]:
    artifact = _load_artifact(model_path)
    return {
        "trained_at": artifact["trained_at"],
        "n_training_rows": artifact["n_training_rows"],
        "metric_unit": artifact["metric_unit"],
        "metrics": artifact["metrics"],
        "feature_importances": artifact["feature_importances"],
        "zone_categories": artifact["zone_categories"],
    }


def get_model_info() -> dict[str, Any]:
    return _model_info(MODEL_PATH)


def get_deficit_model_info() -> dict[str, Any]:
    return _model_info(DEFICIT_MODEL_PATH)


def _build_feature_row(artifact: dict[str, Any], zone: str) -> tuple[date, pd.DataFrame]:
    if zone not in artifact["zone_categories"]:
        raise NoRecentDataError(
            f"Zone '{zone}' was not present in the training data ({artifact['zone_categories']}). "
            f"The model can't make predictions for a zone it has never seen."
        )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")
        frame = build_prediction_frame(zone)

    if frame.empty:
        raise NoRecentDataError(f"No recent data for zone '{zone}' to build a prediction from.")

    based_on_day: date = pd.Timestamp(frame["day"].iloc[0]).date()
    X = frame[FEATURE_COLUMNS].copy()
    X["zone"] = X["zone"].astype("category").cat.set_categories(artifact["zone_categories"])
    return based_on_day, X


def predict_next_day_price(zone: str) -> dict[str, Any]:
    artifact = _load_artifact(MODEL_PATH)
    based_on_day, X = _build_feature_row(artifact, zone)

    predicted_price = float(artifact["model"].predict(X)[0])
    missing_features = [col for col in FEATURE_COLUMNS if col != "zone" and bool(X[col].isna().iloc[0])]

    return {
        "zone": zone,
        "based_on_day": based_on_day,
        "predicted_date": based_on_day + timedelta(days=1),
        "predicted_avg_price_eur_mwh": predicted_price,
        "missing_features": missing_features,
        "model_trained_at": artifact["trained_at"],
    }


def predict_next_day_deficit_for_zone(zone: str) -> dict[str, Any]:
    """
    Predicted next-day supply/demand balance (production minus
    consumption, MW) for a single real zone. Negative means a predicted
    deficit — the zone is expected to need imports to cover demand.
    """
    artifact = _load_artifact(DEFICIT_MODEL_PATH)
    based_on_day, X = _build_feature_row(artifact, zone)

    predicted_balance = float(artifact["model"].predict(X)[0])
    missing_features = [col for col in FEATURE_COLUMNS if col != "zone" and bool(X[col].isna().iloc[0])]

    return {
        "zone": zone,
        "based_on_day": based_on_day,
        "predicted_balance_mw": predicted_balance,
        "based_on_production_mw": None if X["total_production_mw"].isna().iloc[0] else float(X["total_production_mw"].iloc[0]),
        "based_on_load_mw": None if X["avg_load_mw"].isna().iloc[0] else float(X["avg_load_mw"].iloc[0]),
        "missing_features": missing_features,
        "model_trained_at": artifact["trained_at"],
    }
