"""
forecaster.py — Multi-Model Expense Forecasting Engine ("Crystal Ball")
3 models available: Prophet, XGBoost, LightGBM

Prophet: Time-series native, auto-handles seasonality + Indian holidays
XGBoost: Gradient boosted trees with custom feature engineering (DEFAULT/BEST)
LightGBM: Faster variant, leaf-wise growth

Feature Engineering (XGBoost/LightGBM):
- Lag features (1, 2, 3 months)
- Rolling mean (3-month, 6-month)
- Month, quarter, year encoding
- Is_festive_season flag (Oct-Nov for Diwali season)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models.invoice import Invoice
import logging
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class ExpenseForecaster:
    """
    Multi-model forecasting engine.
    Historical invoice data se future expenses predict karta hai.
    """

    AVAILABLE_MODELS = ["prophet", "xgboost", "lightgbm"]

    def __init__(self):
        self.min_months = 6  # Minimum data required for meaningful forecast

    def get_historical_data(
        self,
        db: Session,
        user_id: str,
        data_type: str = "expenses",
    ) -> pd.DataFrame:
        """
        Database se monthly aggregated data fetch karta hai.

        Args:
            db: Database session
            user_id: User ID
            data_type: "expenses" ya "gst"

        Returns:
            DataFrame with columns: ds (date), y (value)
        """
        if data_type == "gst":
            # GST forecast — total GST per month
            results = db.query(
                func.date_trunc('month', Invoice.invoice_date).label('month'),
                func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst).label('total')
            ).filter(
                Invoice.user_id == user_id,
                Invoice.invoice_date.isnot(None),
            ).group_by(
                func.date_trunc('month', Invoice.invoice_date)
            ).order_by('month').all()
        else:
            # Expense forecast — total amount per month
            results = db.query(
                func.date_trunc('month', Invoice.invoice_date).label('month'),
                func.sum(Invoice.total_amount).label('total')
            ).filter(
                Invoice.user_id == user_id,
                Invoice.invoice_date.isnot(None),
            ).group_by(
                func.date_trunc('month', Invoice.invoice_date)
            ).order_by('month').all()

        if not results:
            return pd.DataFrame(columns=['ds', 'y'])

        data = []
        for row in results:
            data.append({
                'ds': pd.Timestamp(row.month),
                'y': float(row.total or 0),
            })

        df = pd.DataFrame(data)
        return df

    def forecast(
        self,
        db: Session,
        user_id: str,
        model_name: str = "xgboost",
        months_ahead: int = 3,
        forecast_type: str = "expenses",
    ) -> Dict:
        """
        Main forecast method — model select karke predictions generate karta hai.

        Args:
            db: Database session
            user_id: User ID
            model_name: "prophet" | "xgboost" | "lightgbm"
            months_ahead: Kitne months aage predict karna hai
            forecast_type: "expenses" | "gst"

        Returns:
            dict with predictions, historical data, metrics
        """
        # Historical data fetch karo
        df = self.get_historical_data(db, user_id, forecast_type)

        if len(df) < 3:
            return {
                "model_used": model_name,
                "forecast_type": forecast_type,
                "months_ahead": months_ahead,
                "predictions": [],
                "historical": [],
                "metrics": {},
                "message": "Not enough data. Need at least 3 months of invoices.",
            }

        # Agar data kam hai toh simple fallback use karo
        if len(df) < self.min_months:
            logger.info(f"📊 Using linear regression fallback ({len(df)} months < {self.min_months})")
            return self._forecast_linear(df, months_ahead, forecast_type)

        # Selected model se forecast karo
        logger.info(f"🔮 Forecasting with {model_name} ({len(df)} months data, {months_ahead} months ahead)")

        if model_name == "prophet":
            return self._forecast_prophet(df, months_ahead, forecast_type)
        elif model_name == "xgboost":
            return self._forecast_xgboost(df, months_ahead, forecast_type)
        elif model_name == "lightgbm":
            return self._forecast_lightgbm(df, months_ahead, forecast_type)
        else:
            return self._forecast_xgboost(df, months_ahead, forecast_type)

    # ══════════════════════════════════════════════════════════════
    # Prophet Model
    # ══════════════════════════════════════════════════════════════

    def _forecast_prophet(self, df: pd.DataFrame, months_ahead: int, forecast_type: str) -> Dict:
        """
        Facebook/Meta Prophet se forecast.
        Seasonality + Indian holidays automatically handle karta hai.
        """
        try:
            from prophet import Prophet

            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,    # Monthly data hai toh weekly off
                daily_seasonality=False,
                changepoint_prior_scale=0.05,  # Trend flexibility control
            )

            # Indian holidays add karo
            model.add_country_holidays(country_name='IN')

            # Model fit karo
            model.fit(df)

            # Future dates create karo
            future = model.make_future_dataframe(periods=months_ahead, freq='MS')
            forecast = model.predict(future)

            # Results format karo
            predictions = []
            historical = []

            for _, row in forecast.iterrows():
                point = {
                    "date": row['ds'].strftime("%Y-%m"),
                    "predicted_value": round(max(0, row['yhat']), 2),
                    "lower_bound": round(max(0, row['yhat_lower']), 2),
                    "upper_bound": round(max(0, row['yhat_upper']), 2),
                }

                # Check if this is historical or prediction
                actual = df[df['ds'] == row['ds']]
                if not actual.empty:
                    point["actual_value"] = round(float(actual['y'].values[0]), 2)
                    historical.append(point)
                else:
                    predictions.append(point)

            # Metrics calculate karo (in-sample)
            metrics = self._calculate_metrics(df['y'].values, forecast['yhat'].values[:len(df)])

            return {
                "model_used": "prophet",
                "forecast_type": forecast_type,
                "months_ahead": months_ahead,
                "predictions": predictions,
                "historical": historical,
                "metrics": metrics,
                "message": f"Prophet forecast: {months_ahead} months ahead with Indian holidays",
            }

        except ImportError:
            logger.warning("⚠️ Prophet not installed, falling back to XGBoost")
            return self._forecast_xgboost(df, months_ahead, forecast_type)

    # ══════════════════════════════════════════════════════════════
    # XGBoost Model (DEFAULT/BEST)
    # ══════════════════════════════════════════════════════════════

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Time-series features create karta hai XGBoost/LightGBM ke liye.

        Features:
        - month, quarter, year (temporal encoding)
        - lag_1, lag_2, lag_3 (previous months' values)
        - rolling_mean_3, rolling_mean_6 (moving averages)
        - is_festive (Oct-Nov Diwali season, Dec year-end)
        - month_sin, month_cos (cyclical encoding)
        """
        features = df.copy()
        features = features.sort_values('ds').reset_index(drop=True)

        # Temporal features
        features['month'] = features['ds'].dt.month
        features['quarter'] = features['ds'].dt.quarter
        features['year'] = features['ds'].dt.year

        # Cyclical encoding — month ko sin/cos mein convert karo
        # Ye model ko batata hai ki Dec (12) aur Jan (1) close hain
        features['month_sin'] = np.sin(2 * np.pi * features['month'] / 12)
        features['month_cos'] = np.cos(2 * np.pi * features['month'] / 12)

        # Lag features — pichle months ke values
        features['lag_1'] = features['y'].shift(1)
        features['lag_2'] = features['y'].shift(2)
        features['lag_3'] = features['y'].shift(3)

        # Rolling statistics — moving averages
        features['rolling_mean_3'] = features['y'].rolling(window=3, min_periods=1).mean()
        features['rolling_mean_6'] = features['y'].rolling(window=6, min_periods=1).mean()
        features['rolling_std_3'] = features['y'].rolling(window=3, min_periods=1).std().fillna(0)

        # Festive season flag — Diwali (Oct-Nov) + Year-end (Dec)
        # Indian SMEs mein festive season pe spending badh jaati hai
        features['is_festive'] = features['month'].isin([10, 11, 12]).astype(int)

        # Year-over-year growth (agar 12+ months data hai)
        features['lag_12'] = features['y'].shift(12)
        features['yoy_growth'] = (features['y'] - features['lag_12']) / features['lag_12'].replace(0, np.nan)
        features['yoy_growth'] = features['yoy_growth'].fillna(0)

        # NaN fill karo (lag features ke liye)
        features = features.fillna(method='bfill').fillna(0)

        return features

    def _get_feature_columns(self) -> List[str]:
        """Feature columns ki list return karta hai"""
        return [
            'month', 'quarter', 'year',
            'month_sin', 'month_cos',
            'lag_1', 'lag_2', 'lag_3',
            'rolling_mean_3', 'rolling_mean_6', 'rolling_std_3',
            'is_festive', 'lag_12', 'yoy_growth',
        ]

    def _forecast_xgboost(self, df: pd.DataFrame, months_ahead: int, forecast_type: str) -> Dict:
        """
        XGBoost Gradient Boosted Trees se forecast.
        Custom feature engineering — lag, rolling mean, cyclical encoding.
        """
        try:
            from xgboost import XGBRegressor
            from sklearn.model_selection import TimeSeriesSplit
            from sklearn.metrics import mean_absolute_error, mean_squared_error

            # Features create karo
            features_df = self._create_features(df)
            feature_cols = self._get_feature_columns()

            X = features_df[feature_cols].values
            y = features_df['y'].values

            # Train-test split (last 20% for validation)
            split_idx = max(1, int(len(X) * 0.8))
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # XGBoost model train karo
            model = XGBRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,           # L1 regularization
                reg_lambda=1.0,          # L2 regularization
                random_state=42,
                verbosity=0,
            )
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

            # Historical predictions (in-sample)
            historical_preds = model.predict(X)
            historical = []
            for i, row in features_df.iterrows():
                historical.append({
                    "date": row['ds'].strftime("%Y-%m"),
                    "predicted_value": round(max(0, float(historical_preds[i])), 2),
                    "lower_bound": round(max(0, float(historical_preds[i]) * 0.85), 2),
                    "upper_bound": round(float(historical_preds[i]) * 1.15, 2),
                    "actual_value": round(float(row['y']), 2),
                })

            # Future predictions — iteratively predict karo
            predictions = []
            last_features = features_df.copy()

            for m in range(months_ahead):
                # Next month ka date
                last_date = last_features['ds'].max()
                next_date = last_date + pd.DateOffset(months=1)

                # Next month ke features create karo
                next_row = {
                    'ds': next_date,
                    'y': 0,  # Placeholder, prediction se replace hoga
                    'month': next_date.month,
                    'quarter': next_date.quarter,
                    'year': next_date.year,
                    'month_sin': np.sin(2 * np.pi * next_date.month / 12),
                    'month_cos': np.cos(2 * np.pi * next_date.month / 12),
                    'lag_1': float(last_features['y'].iloc[-1]),
                    'lag_2': float(last_features['y'].iloc[-2]) if len(last_features) > 1 else 0,
                    'lag_3': float(last_features['y'].iloc[-3]) if len(last_features) > 2 else 0,
                    'rolling_mean_3': float(last_features['y'].tail(3).mean()),
                    'rolling_mean_6': float(last_features['y'].tail(6).mean()),
                    'rolling_std_3': float(last_features['y'].tail(3).std()) if len(last_features) >= 3 else 0,
                    'is_festive': 1 if next_date.month in [10, 11, 12] else 0,
                    'lag_12': float(last_features['y'].iloc[-12]) if len(last_features) >= 12 else 0,
                    'yoy_growth': 0,
                }

                # Predict karo
                X_next = np.array([[next_row[col] for col in feature_cols]])
                pred = float(model.predict(X_next)[0])
                pred = max(0, pred)  # Negative prediction na ho

                # Confidence interval (±15% simple estimate)
                std_factor = float(last_features['y'].std()) * 0.3 if len(last_features) > 1 else pred * 0.15

                predictions.append({
                    "date": next_date.strftime("%Y-%m"),
                    "predicted_value": round(pred, 2),
                    "lower_bound": round(max(0, pred - std_factor), 2),
                    "upper_bound": round(pred + std_factor, 2),
                })

                # Predicted value ko data mein add karo (next iteration ke liye)
                next_row['y'] = pred
                next_df = pd.DataFrame([next_row])
                last_features = pd.concat([last_features, next_df], ignore_index=True)

            # Metrics
            if len(y_test) > 0:
                test_preds = model.predict(X_test)
                metrics = {
                    "mae": round(float(mean_absolute_error(y_test, test_preds)), 2),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_test, test_preds))), 2),
                    "mape": round(float(np.mean(np.abs((y_test - test_preds) / np.where(y_test == 0, 1, y_test))) * 100), 2),
                }
            else:
                metrics = {}

            return {
                "model_used": "xgboost",
                "forecast_type": forecast_type,
                "months_ahead": months_ahead,
                "predictions": predictions,
                "historical": historical,
                "metrics": metrics,
                "message": f"XGBoost forecast with {len(feature_cols)} engineered features",
            }

        except ImportError:
            logger.warning("⚠️ XGBoost not installed, falling back to linear regression")
            return self._forecast_linear(df, months_ahead, forecast_type)

    # ══════════════════════════════════════════════════════════════
    # LightGBM Model
    # ══════════════════════════════════════════════════════════════

    def _forecast_lightgbm(self, df: pd.DataFrame, months_ahead: int, forecast_type: str) -> Dict:
        """
        LightGBM se forecast — XGBoost jaisi feature engineering,
        but faster training (leaf-wise growth strategy).
        """
        try:
            import lightgbm as lgb
            from sklearn.metrics import mean_absolute_error, mean_squared_error

            features_df = self._create_features(df)
            feature_cols = self._get_feature_columns()

            X = features_df[feature_cols].values
            y = features_df['y'].values

            split_idx = max(1, int(len(X) * 0.8))
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # LightGBM model
            model = lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                num_leaves=31,          # Leaf-wise growth
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                verbose=-1,
            )
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)])

            # Historical
            historical_preds = model.predict(X)
            historical = []
            for i, row in features_df.iterrows():
                historical.append({
                    "date": row['ds'].strftime("%Y-%m"),
                    "predicted_value": round(max(0, float(historical_preds[i])), 2),
                    "lower_bound": round(max(0, float(historical_preds[i]) * 0.85), 2),
                    "upper_bound": round(float(historical_preds[i]) * 1.15, 2),
                    "actual_value": round(float(row['y']), 2),
                })

            # Future predictions
            predictions = []
            last_features = features_df.copy()

            for m in range(months_ahead):
                last_date = last_features['ds'].max()
                next_date = last_date + pd.DateOffset(months=1)

                next_row = {
                    'ds': next_date, 'y': 0,
                    'month': next_date.month, 'quarter': next_date.quarter, 'year': next_date.year,
                    'month_sin': np.sin(2 * np.pi * next_date.month / 12),
                    'month_cos': np.cos(2 * np.pi * next_date.month / 12),
                    'lag_1': float(last_features['y'].iloc[-1]),
                    'lag_2': float(last_features['y'].iloc[-2]) if len(last_features) > 1 else 0,
                    'lag_3': float(last_features['y'].iloc[-3]) if len(last_features) > 2 else 0,
                    'rolling_mean_3': float(last_features['y'].tail(3).mean()),
                    'rolling_mean_6': float(last_features['y'].tail(6).mean()),
                    'rolling_std_3': float(last_features['y'].tail(3).std()) if len(last_features) >= 3 else 0,
                    'is_festive': 1 if next_date.month in [10, 11, 12] else 0,
                    'lag_12': float(last_features['y'].iloc[-12]) if len(last_features) >= 12 else 0,
                    'yoy_growth': 0,
                }

                X_next = np.array([[next_row[col] for col in feature_cols]])
                pred = max(0, float(model.predict(X_next)[0]))

                std_factor = float(last_features['y'].std()) * 0.3 if len(last_features) > 1 else pred * 0.15

                predictions.append({
                    "date": next_date.strftime("%Y-%m"),
                    "predicted_value": round(pred, 2),
                    "lower_bound": round(max(0, pred - std_factor), 2),
                    "upper_bound": round(pred + std_factor, 2),
                })

                next_row['y'] = pred
                next_df = pd.DataFrame([next_row])
                last_features = pd.concat([last_features, next_df], ignore_index=True)

            # Metrics
            if len(y_test) > 0:
                test_preds = model.predict(X_test)
                metrics = {
                    "mae": round(float(mean_absolute_error(y_test, test_preds)), 2),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_test, test_preds))), 2),
                    "mape": round(float(np.mean(np.abs((y_test - test_preds) / np.where(y_test == 0, 1, y_test))) * 100), 2),
                }
            else:
                metrics = {}

            return {
                "model_used": "lightgbm",
                "forecast_type": forecast_type,
                "months_ahead": months_ahead,
                "predictions": predictions,
                "historical": historical,
                "metrics": metrics,
                "message": f"LightGBM forecast (leaf-wise growth, faster training)",
            }

        except ImportError:
            logger.warning("⚠️ LightGBM not installed, falling back to XGBoost")
            return self._forecast_xgboost(df, months_ahead, forecast_type)

    # ══════════════════════════════════════════════════════════════
    # Linear Regression Fallback (< 6 months data)
    # ══════════════════════════════════════════════════════════════

    def _forecast_linear(self, df: pd.DataFrame, months_ahead: int, forecast_type: str) -> Dict:
        """Simple linear regression — kam data ke liye fallback"""
        from sklearn.linear_model import LinearRegression

        X = np.arange(len(df)).reshape(-1, 1)
        y = df['y'].values

        model = LinearRegression()
        model.fit(X, y)

        historical = []
        preds = model.predict(X)
        for i, row in df.iterrows():
            historical.append({
                "date": row['ds'].strftime("%Y-%m"),
                "predicted_value": round(max(0, float(preds[i])), 2),
                "lower_bound": round(max(0, float(preds[i]) * 0.8), 2),
                "upper_bound": round(float(preds[i]) * 1.2, 2),
                "actual_value": round(float(row['y']), 2),
            })

        predictions = []
        for m in range(months_ahead):
            x_next = len(df) + m
            pred = max(0, float(model.predict([[x_next]])[0]))
            next_date = df['ds'].max() + pd.DateOffset(months=m + 1)
            predictions.append({
                "date": next_date.strftime("%Y-%m"),
                "predicted_value": round(pred, 2),
                "lower_bound": round(max(0, pred * 0.8), 2),
                "upper_bound": round(pred * 1.2, 2),
            })

        return {
            "model_used": "linear_regression",
            "forecast_type": forecast_type,
            "months_ahead": months_ahead,
            "predictions": predictions,
            "historical": historical,
            "metrics": {"note": "Linear fallback — need 6+ months for advanced models"},
            "message": f"Linear regression fallback (only {len(df)} months data available)",
        }

    # ══════════════════════════════════════════════════════════════
    # Metrics Helper
    # ══════════════════════════════════════════════════════════════

    def _calculate_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> Dict:
        """MAE, RMSE, MAPE calculate karta hai"""
        from sklearn.metrics import mean_absolute_error, mean_squared_error

        n = min(len(actual), len(predicted))
        actual = actual[:n]
        predicted = predicted[:n]

        mae = float(mean_absolute_error(actual, predicted))
        rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
        mape = float(np.mean(np.abs((actual - predicted) / np.where(actual == 0, 1, actual))) * 100)

        return {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mape": round(mape, 2),
        }
