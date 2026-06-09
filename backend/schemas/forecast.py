"""
schemas/forecast.py — Pydantic Schemas for Forecasting API
Prophet, XGBoost, aur LightGBM ke predictions ka format define karta hai.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class ForecastRequest(BaseModel):
    """Forecast API ke liye request body"""
    months_ahead: int = Field(default=3, ge=1, le=12, description="Kitne months aage forecast karna hai")
    model: str = Field(default="xgboost", description="Model select karo: prophet | xgboost | lightgbm")
    forecast_type: str = Field(default="expenses", description="Kya forecast karna hai: expenses | gst")


class ForecastDataPoint(BaseModel):
    """Ek single prediction data point"""
    date: str                                # YYYY-MM format
    predicted_value: float                   # Predicted amount (yhat)
    lower_bound: float                       # Confidence interval lower
    upper_bound: float                       # Confidence interval upper
    actual_value: Optional[float] = None     # Past data ke liye actual value


class ForecastResponse(BaseModel):
    """Forecast endpoint ka full response"""
    model_used: str                          # prophet | xgboost | lightgbm
    forecast_type: str                       # expenses | gst
    months_ahead: int
    predictions: List[ForecastDataPoint]     # Future predictions
    historical: List[ForecastDataPoint]      # Past data points (chart ke liye)
    metrics: dict = {}                       # Model performance metrics (MAE, RMSE, etc.)
    message: str = "Forecast generated successfully"


class ModelComparisonResponse(BaseModel):
    """Saare models ka comparison — Predictions page pe dikhega"""
    prophet: Optional[ForecastResponse] = None
    xgboost: Optional[ForecastResponse] = None
    lightgbm: Optional[ForecastResponse] = None
    best_model: str = "xgboost"              # Best model recommendation
    comparison_metrics: dict = {}            # Side-by-side metrics
