"""Load business metrics from Excel or CSV files."""

from pathlib import Path

import pandas as pd


DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "business_metrics.xlsx"


def load_metrics(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load a tabular metrics file and normalize its column names."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Data file not found: {source}")
    if source.stat().st_size == 0:
        raise ValueError(f"Data file is empty: {source}")

    suffix = source.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(source)
    elif suffix == ".csv":
        frame = pd.read_csv(source)
    else:
        raise ValueError("Supported data formats are .xlsx, .xls, and .csv")

    if frame.empty:
        raise ValueError(f"Data file contains no rows: {source}")

    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    return frame


def infer_time_column(frame: pd.DataFrame) -> str | None:
    """Return the first likely time column, if one exists."""
    candidates = {"date", "datetime", "timestamp", "time", "period"}
    for column in frame.columns:
        if column in candidates or any(term in column for term in ("date", "time", "timestamp")):
            return column
    return None
