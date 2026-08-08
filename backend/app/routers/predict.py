from fastapi import APIRouter, HTTPException, Query

from ..ml.predict import ModelNotTrainedError, NoRecentDataError, get_model_info, predict_next_day_price
from ..schemas import ModelInfo, PricePrediction
from ..zones import validate_zone

router = APIRouter(prefix="/predict", tags=["predict"])


@router.get("/price", response_model=PricePrediction)
def predict_price(zone: str = Query(..., description="Zone code, e.g. NO1.")):
    """
    Predicted next-day average spot price for a zone, from a gradient
    boosting model trained on lagged price, production mix, reservoir
    fill, weather and cross-border flow.
    """
    validate_zone(zone)
    try:
        return PricePrediction(**predict_next_day_price(zone))
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except NoRecentDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/model-info", response_model=ModelInfo)
def model_info():
    """Metadata about the currently loaded prediction model: when it was trained, holdout metrics, feature importances."""
    try:
        return ModelInfo(**get_model_info())
    except ModelNotTrainedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
