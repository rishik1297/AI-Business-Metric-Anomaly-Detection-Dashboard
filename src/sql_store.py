"""SQLite storage for normalized business metric observations."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .ai_explainer import _metric_metadata


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "reports" / "metrics.db"
DEFAULT_POWERBI_EXPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "powerbi"


@contextmanager
def _connect(database_path: str | Path = DEFAULT_DATABASE_PATH):
    """Open a SQLite connection and always close it after use."""
    database = Path(database_path)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Create the observation table and indexes if they do not exist."""
    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metric_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_date TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_position INTEGER NOT NULL,
                metric_value REAL NOT NULL,
                source_name TEXT NOT NULL,
                source_fingerprint TEXT NOT NULL,
                loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_fingerprint, observation_date, metric_name)
            );
            CREATE INDEX IF NOT EXISTS idx_metric_observations_date
                ON metric_observations(observation_date);
            CREATE INDEX IF NOT EXISTS idx_metric_observations_metric
                ON metric_observations(metric_name);
            CREATE INDEX IF NOT EXISTS idx_metric_observations_source
                ON metric_observations(source_fingerprint);
            CREATE TABLE IF NOT EXISTS anomaly_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_date TEXT NOT NULL,
                metric TEXT NOT NULL,
                score REAL NOT NULL,
                severity TEXT NOT NULL,
                alert TEXT NOT NULL,
                source_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_fingerprint, alert_date, metric)
            );
            CREATE INDEX IF NOT EXISTS idx_anomaly_history_date
                ON anomaly_history(alert_date);
            CREATE INDEX IF NOT EXISTS idx_anomaly_history_source
                ON anomaly_history(source_fingerprint);
            """
        )


def fingerprint_frame(frame: pd.DataFrame, source_name: str) -> str:
    """Return a stable identity for one source and its contents."""
    payload = source_name.encode("utf-8") + b"\n" + frame.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def frame_to_observations(
    frame: pd.DataFrame,
    time_column: str | None,
    source_name: str,
    source_fingerprint: str,
) -> list[tuple[str, str, float, str, str]]:
    """Convert a wide metric frame into SQL-ready long-form rows."""
    if not time_column or time_column not in frame.columns:
        raise ValueError("A date or period column is required before loading data into SQL")

    numeric_columns = frame.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        raise ValueError("No numeric metric columns were found for SQL loading")

    observations = []
    for _, row in frame.iterrows():
        observation_date = pd.to_datetime(row[time_column], errors="coerce")
        if pd.isna(observation_date):
            raise ValueError("Every row must contain a valid date or period for SQL loading")
        date_value = observation_date.isoformat()
        for metric_position, metric_name in enumerate(numeric_columns):
            metric_value = row[metric_name]
            if pd.notna(metric_value):
                observations.append(
                    (
                        date_value,
                        metric_name,
                        metric_position,
                        float(metric_value),
                        source_name,
                        source_fingerprint,
                    )
                )
    return observations


def import_frame(
    frame: pd.DataFrame,
    time_column: str | None,
    source_name: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> str:
    """Upsert a source frame and return its content fingerprint."""
    initialize_database(database_path)
    source_fingerprint = fingerprint_frame(frame, source_name)
    observations = frame_to_observations(
        frame, time_column, source_name, source_fingerprint
    )
    with _connect(database_path) as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO metric_observations
                (observation_date, metric_name, metric_position, metric_value,
                 source_name, source_fingerprint)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            observations,
        )
    return source_fingerprint


def query_metrics(
    source_fingerprint: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> pd.DataFrame:
    """Query one imported source and pivot it back to wide metric columns."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT observation_date, metric_name, metric_position, metric_value
            FROM metric_observations
            WHERE source_fingerprint = ?
            ORDER BY observation_date, metric_position
            """,
            (source_fingerprint,),
        ).fetchall()

    if not rows:
        raise ValueError("No SQL observations found for the selected source")
    observations = pd.DataFrame(
        rows,
        columns=["observation_date", "metric_name", "metric_position", "metric_value"],
    )
    metric_order = (
        observations[["metric_name", "metric_position"]]
        .drop_duplicates()
        .sort_values("metric_position")["metric_name"]
        .tolist()
    )
    wide = observations.pivot(index="observation_date", columns="metric_name", values="metric_value")
    wide = wide.reindex(columns=metric_order)
    wide = wide.reset_index().rename(columns={"observation_date": "date"})
    wide["date"] = pd.to_datetime(wide["date"])
    wide.columns.name = None
    return wide


def count_observations(
    source_fingerprint: str | None = None,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> int:
    """Return the number of stored observations, optionally for one source."""
    initialize_database(database_path)
    query = "SELECT COUNT(*) FROM metric_observations"
    parameters: tuple[str, ...] = ()
    if source_fingerprint:
        query += " WHERE source_fingerprint = ?"
        parameters = (source_fingerprint,)
    with _connect(database_path) as connection:
        return int(connection.execute(query, parameters).fetchone()[0])


def _severity(score: float) -> str:
    if score >= 0.20:
        return "Critical"
    if score >= 0.10:
        return "High"
    if score >= 0.03:
        return "Medium"
    return "Low"


def _history_rows(
    detected: pd.DataFrame,
    feature_columns: list[str],
    source_fingerprint: str,
) -> list[tuple[str, str, float, str, str, str]]:
    normal = detected.loc[~detected["is_anomaly"], feature_columns]
    baseline_frame = normal if not normal.empty else detected[feature_columns]
    means = baseline_frame.mean()
    rows = []
    for _, row in detected.loc[detected["is_anomaly"]].iterrows():
        alert_date = row.get("date")
        if pd.isna(alert_date):
            alert_date = pd.Timestamp.now()
        alert_date = pd.to_datetime(alert_date).date().isoformat()
        deviations = (row[feature_columns] - means).abs().sort_values(ascending=False)
        for metric_name in deviations.head(3).index:
            rows.append(
                (
                    alert_date,
                    _metric_metadata(metric_name)["label"],
                    float(row["anomaly_score"]),
                    _severity(float(row["anomaly_score"])),
                    str(row.get("explanation", "Anomalous business metric pattern.")),
                    source_fingerprint,
                )
            )
    return rows


def record_anomalies(
    detected: pd.DataFrame,
    feature_columns: list[str],
    source_fingerprint: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> int:
    """Store new anomaly-driver alerts and return the inserted row count."""
    initialize_database(database_path)
    rows = _history_rows(detected, feature_columns, source_fingerprint)
    with _connect(database_path) as connection:
        before = connection.total_changes
        connection.executemany(
            """
            INSERT OR IGNORE INTO anomaly_history
                (alert_date, metric, score, severity, alert, source_fingerprint)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return connection.total_changes - before


def query_anomaly_history(
    month: str | None = None,
    source_fingerprint: str | None = None,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> pd.DataFrame:
    """Return alert history, optionally filtered by YYYY-MM and source."""
    initialize_database(database_path)
    clauses = []
    parameters: list[str] = []
    if month:
        clauses.append("substr(alert_date, 1, 7) = ?")
        parameters.append(month)
    if source_fingerprint:
        clauses.append("source_fingerprint = ?")
        parameters.append(source_fingerprint)
    query = "SELECT alert_date, metric, score, severity, alert FROM anomaly_history"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY alert_date DESC, score DESC, metric"
    with _connect(database_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return pd.DataFrame(rows, columns=["Date", "Metric", "Score", "Severity", "Alert"])


def query_history_months(
    source_fingerprint: str | None = None,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> list[str]:
    """Return available alert months in descending order."""
    initialize_database(database_path)
    query = "SELECT DISTINCT substr(alert_date, 1, 7) AS month FROM anomaly_history"
    parameters: tuple[str, ...] = ()
    if source_fingerprint:
        query += " WHERE source_fingerprint = ?"
        parameters = (source_fingerprint,)
    query += " ORDER BY month DESC"
    with _connect(database_path) as connection:
        return [row[0] for row in connection.execute(query, parameters).fetchall()]


def export_metric_observations(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    export_directory: str | Path = DEFAULT_POWERBI_EXPORT_DIR,
) -> Path:
    """Export normalized metric observations for Power BI."""
    initialize_database(database_path)
    export_path = Path(export_directory)
    export_path.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        observations = pd.read_sql_query(
            """
            SELECT observation_date, metric_name, metric_position, metric_value,
                   source_name, source_fingerprint, loaded_at
            FROM metric_observations
            ORDER BY observation_date, metric_position
            """,
            connection,
        )
    output_path = export_path / "metric_observations.csv"
    observations.to_csv(output_path, index=False)
    return output_path


def export_anomaly_history(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    export_directory: str | Path = DEFAULT_POWERBI_EXPORT_DIR,
) -> Path:
    """Export anomaly history for Power BI."""
    initialize_database(database_path)
    export_path = Path(export_directory)
    export_path.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        history = pd.read_sql_query(
            """
            SELECT alert_date AS Date, metric AS Metric, score AS Score,
                   severity AS Severity, alert AS Alert
            FROM anomaly_history
            ORDER BY alert_date DESC, score DESC, metric
            """,
            connection,
        )
    output_path = export_path / "anomaly_history.csv"
    history.to_csv(output_path, index=False)
    return output_path
