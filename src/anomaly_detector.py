"""Isolation Forest based anomaly detection."""

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def detect_anomalies(
    frame: pd.DataFrame,
    feature_columns: list[str],
    contamination: float = 0.05,
    random_state: int = 42,
) -> tuple[pd.DataFrame, IsolationForest]:
    """Score rows and append anomaly labels and scores."""
    if len(frame) < 3:
        raise ValueError("At least three rows are required for anomaly detection")
    if not 0 < contamination <= 0.5:
        raise ValueError("contamination must be between 0 and 0.5")

    values = StandardScaler().fit_transform(frame[feature_columns])
    model = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=200,
    )
    model.fit(values)
    result = frame.copy()
    result["anomaly_score"] = -model.decision_function(values)
    result["is_anomaly"] = model.predict(values) == -1
    result["anomaly_rank"] = result["anomaly_score"].rank(method="first", ascending=False).astype(int)
    return result.sort_values("anomaly_score", ascending=False).reset_index(drop=True), model
