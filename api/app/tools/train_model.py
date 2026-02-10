"""TrainModelTool - Train supervised ML models on tabular data using scikit-learn."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Max unique values for a numeric column to be treated as classification
_CLASSIFICATION_THRESHOLD = 20


class TrainModelTool:
    """Train supervised ML models and save predictions for residual analysis."""

    name = "train_model"
    description = "Train a supervised ML model on tabular data."

    def __init__(self, data_loader: Any) -> None:
        self._loader = data_loader

    def execute(
        self,
        table: str,
        target: str,
        features: list[str] | None = None,
        model_type: str = "auto",
        algorithm: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
        split_by: str | None = None,
    ) -> dict:
        # Load data
        try:
            df = self._loader.get_table(table)
        except Exception as exc:
            return {"error": f"Unable to load table '{table}': {exc}"}

        # Validate target
        if target not in df.columns:
            return {"error": f"Target column '{target}' not found. Available: {list(df.columns)}"}

        # Resolve features
        if features:
            missing = [f for f in features if f not in df.columns]
            if missing:
                return {"error": f"Feature columns not found: {missing}"}
            feature_cols = list(features)
        else:
            feature_cols = self._auto_select_features(df, target)

        if not feature_cols:
            return {"error": "No usable feature columns found."}

        # Determine model type
        resolved_type = self._resolve_model_type(model_type, df[target])

        # Prepare feature matrix
        X, used_feature_names = self._prepare_features(df, feature_cols)
        y = df[target].copy()

        # Drop rows with NaN in features or target
        mask = X.notna().all(axis=1) & y.notna()
        X = X.loc[mask]
        y = y.loc[mask]

        if len(X) < 2:
            return {"error": "Not enough valid rows after dropping NaNs (need at least 2)."}

        # Encode target for classification if needed
        label_encoder = None
        if resolved_type == "classification" and y.dtype == object:
            label_encoder = LabelEncoder()
            y = pd.Series(label_encoder.fit_transform(y), index=y.index)

        # Train/test split
        if split_by is not None:
            if split_by not in df.columns:
                return {"error": f"split_by column '{split_by}' not found. Available: {list(df.columns)}"}
            col = df.loc[mask, split_by]
            if not (pd.api.types.is_numeric_dtype(col) or pd.api.types.is_datetime64_any_dtype(col)):
                return {"error": f"split_by column '{split_by}' is not sortable (must be numeric or datetime)."}

            sorted_idx = col.values.argsort()
            X = X.iloc[sorted_idx].reset_index(drop=True)
            y = y.iloc[sorted_idx].reset_index(drop=True)
            mask_indices = mask[mask].index
            sorted_mask_indices = mask_indices[sorted_idx]
            df_clean = df.loc[sorted_mask_indices].reset_index(drop=True)

            split_point = int(len(X) * (1 - test_size))
            X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
            y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]
        else:
            df_clean = df.loc[mask]
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state,
                )
            except ValueError as exc:
                return {"error": f"Could not split data: {exc}"}

        # Select and train model
        model = self._create_model(resolved_type, algorithm, random_state)
        try:
            model.fit(X_train, y_train)
        except Exception as exc:
            return {"error": f"Training failed: {exc}"}

        # Compute metrics
        metrics = self._compute_metrics(
            model, X_train, y_train, X_test, y_test, resolved_type,
        )

        # Feature importances
        feature_importances = self._get_feature_importances(model, used_feature_names)

        # Build predictions DataFrame
        pred_df = self._build_predictions_df(
            df_clean, X, y, model, target, resolved_type,
            X_train.index, X_test.index, label_encoder,
        )
        predictions_table = f"{target}_predictions"
        self._loader.register_dataframe(predictions_table, pred_df)

        # Report feature names: collapse one-hot back to original column names for readability
        reported_features = feature_cols if features else feature_cols

        message = (
            f"Model trained. Predictions saved to '{predictions_table}'. "
            "Use run_sql to analyze residuals."
        )

        result = {
            "model_type": resolved_type,
            "algorithm": algorithm,
            "target": target,
            "features_used": reported_features,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "metrics": metrics,
            "feature_importances": feature_importances,
            "predictions_table": predictions_table,
            "message": message,
        }
        if split_by is not None:
            result["split_by"] = split_by
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auto_select_features(self, df: pd.DataFrame, target: str) -> list[str]:
        """Select features automatically: numeric cols + low-cardinality categoricals."""
        cols = []
        for col in df.columns:
            if col == target:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                cols.append(col)
            elif pd.api.types.is_string_dtype(df[col]) and 1 < df[col].nunique() <= 50:
                cols.append(col)
        return cols

    def _resolve_model_type(self, model_type: str, target_series: pd.Series) -> str:
        if model_type in ("regression", "classification"):
            return model_type
        # auto-detect
        if pd.api.types.is_string_dtype(target_series) or target_series.dtype.name == "category":
            return "classification"
        if target_series.dtype == bool:
            return "classification"
        if target_series.nunique() <= _CLASSIFICATION_THRESHOLD:
            return "classification"
        return "regression"

    def _prepare_features(
        self, df: pd.DataFrame, feature_cols: list[str],
    ) -> tuple[pd.DataFrame, list[str]]:
        """Build feature matrix with one-hot encoding for categoricals."""
        parts: list[pd.DataFrame] = []
        names: list[str] = []
        for col in feature_cols:
            if pd.api.types.is_numeric_dtype(df[col]):
                parts.append(df[[col]])
                names.append(col)
            elif pd.api.types.is_string_dtype(df[col]):
                dummies = pd.get_dummies(df[col], prefix=col, drop_first=False, dtype=float)
                parts.append(dummies)
                names.extend(dummies.columns.tolist())
            else:
                dummies = pd.get_dummies(df[col], prefix=col, drop_first=False, dtype=float)
                parts.append(dummies)
                names.extend(dummies.columns.tolist())
        X = pd.concat(parts, axis=1)
        return X, names

    def _create_model(self, model_type: str, algorithm: str, random_state: int) -> Any:
        if model_type == "regression":
            if algorithm == "gradient_boosting":
                return GradientBoostingRegressor(random_state=random_state)
            if algorithm == "linear":
                return LinearRegression()
            return RandomForestRegressor(n_estimators=100, random_state=random_state)
        else:
            if algorithm == "gradient_boosting":
                return GradientBoostingClassifier(random_state=random_state)
            if algorithm == "linear":
                return LogisticRegression(random_state=random_state, max_iter=1000)
            return RandomForestClassifier(n_estimators=100, random_state=random_state)

    def _compute_metrics(
        self,
        model: Any,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_type: str,
    ) -> dict:
        metrics: dict[str, dict] = {}
        for split_name, X, y in [("train", X_train, y_train), ("test", X_test, y_test)]:
            preds = model.predict(X)
            if model_type == "regression":
                metrics[split_name] = {
                    "r2": float(r2_score(y, preds)),
                    "mae": float(mean_absolute_error(y, preds)),
                    "rmse": float(np.sqrt(mean_squared_error(y, preds))),
                }
            else:
                metrics[split_name] = {
                    "accuracy": float(accuracy_score(y, preds)),
                    "f1": float(f1_score(y, preds, average="weighted")),
                }
        return metrics

    def _get_feature_importances(
        self, model: Any, feature_names: list[str],
    ) -> list[dict]:
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.abs(model.coef_).flatten()
            if len(importances) != len(feature_names):
                # multi-class: average across classes
                importances = np.abs(model.coef_).mean(axis=0)
        else:
            return []

        pairs = sorted(
            zip(feature_names, importances.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return [{"feature": f, "importance": round(v, 6)} for f, v in pairs]

    def _build_predictions_df(
        self,
        original_df: pd.DataFrame,
        X: pd.DataFrame,
        y: pd.Series,
        model: Any,
        target: str,
        model_type: str,
        train_idx: pd.Index,
        test_idx: pd.Index,
        label_encoder: LabelEncoder | None,
    ) -> pd.DataFrame:
        preds = model.predict(X)
        if label_encoder is not None:
            preds = label_encoder.inverse_transform(preds)

        pred_df = original_df.reset_index(drop=True).copy()
        pred_col = f"predicted_{target}"
        pred_df[pred_col] = preds

        if model_type == "regression":
            pred_df["residual"] = pred_df[target].astype(float) - pred_df[pred_col].astype(float)

        # Mark train/test split
        split_labels = pd.Series("train", index=X.index)
        split_labels.loc[test_idx] = "test"
        pred_df["split"] = split_labels.values

        return pred_df
