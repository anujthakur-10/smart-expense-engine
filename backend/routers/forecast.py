"""
forecast.py — Forecasting API Router
Multi-model predictions: Prophet, XGBoost, LightGBM.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from services.forecaster import ExpenseForecaster
from schemas.forecast import ForecastResponse, ModelComparisonResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forecast", tags=["Forecast"])

forecaster = ExpenseForecaster()


@router.get("/expenses", response_model=ForecastResponse)
async def forecast_expenses(
    months_ahead: int = Query(3, ge=1, le=12),
    model: str = Query("xgboost", regex="^(prophet|xgboost|lightgbm)$"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Expense forecast — selected model se future expenses predict karo.
    Default: XGBoost (best performance).
    """
    result = forecaster.forecast(
        db=db,
        user_id=user["id"],
        model_name=model,
        months_ahead=months_ahead,
        forecast_type="expenses",
    )
    return ForecastResponse(**result)


@router.get("/gst", response_model=ForecastResponse)
async def forecast_gst(
    months_ahead: int = Query(3, ge=1, le=12),
    model: str = Query("xgboost", regex="^(prophet|xgboost|lightgbm)$"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """GST liability forecast — next N months mein kitna GST dena padega"""
    result = forecaster.forecast(
        db=db,
        user_id=user["id"],
        model_name=model,
        months_ahead=months_ahead,
        forecast_type="gst",
    )
    return ForecastResponse(**result)


@router.get("/compare", response_model=ModelComparisonResponse)
async def compare_models(
    months_ahead: int = Query(3, ge=1, le=12),
    forecast_type: str = Query("expenses", regex="^(expenses|gst)$"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Saare 3 models ka comparison — side by side metrics.
    Frontend pe model selection dropdown ke liye useful.
    """
    results = {}
    best_model = "xgboost"
    best_mae = float('inf')

    for model_name in ["prophet", "xgboost", "lightgbm"]:
        try:
            result = forecaster.forecast(
                db=db,
                user_id=user["id"],
                model_name=model_name,
                months_ahead=months_ahead,
                forecast_type=forecast_type,
            )
            results[model_name] = ForecastResponse(**result)

            # Best model find karo (lowest MAE)
            mae = result.get("metrics", {}).get("mae", float('inf'))
            if mae < best_mae:
                best_mae = mae
                best_model = model_name

        except Exception as e:
            logger.warning(f"⚠️ {model_name} forecast failed: {e}")
            results[model_name] = None

    # Comparison metrics build karo
    comparison = {}
    for name, resp in results.items():
        if resp and resp.metrics:
            comparison[name] = resp.metrics

    return ModelComparisonResponse(
        prophet=results.get("prophet"),
        xgboost=results.get("xgboost"),
        lightgbm=results.get("lightgbm"),
        best_model=best_model,
        comparison_metrics=comparison,
    )
