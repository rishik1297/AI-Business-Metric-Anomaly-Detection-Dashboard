"""Prepare business metrics for anomaly detection."""

import pandas as pd

from .data_loader import infer_time_column


def prepare_metrics(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str], str | None]:
    """Coerce numeric fields and return usable features with optional time data."""
    prepared = frame.drop_duplicates().copy()
    time_column = infer_time_column(prepared)
    if time_column:
        prepared[time_column] = pd.to_datetime(prepared[time_column], errors="coerce")

    metric_columns = [column for column in prepared.columns if column != time_column]
    for column in metric_columns:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    numeric_columns = prepared.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        raise ValueError("No numeric metric columns were found in the data")

    prepared[numeric_columns] = prepared[numeric_columns].replace([float("inf"), float("-inf")], pd.NA)
    prepared = prepared.dropna(subset=numeric_columns, how="all").reset_index(drop=True)
    prepared[numeric_columns] = prepared[numeric_columns].fillna(prepared[numeric_columns].median())
    if prepared.empty:
        raise ValueError("No usable rows remain after cleaning the metrics")
    return prepared, numeric_columns, time_column
