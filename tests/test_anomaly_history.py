import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.sql_store import (
    _severity,
    query_anomaly_history,
    query_history_months,
    record_anomalies,
)


class AnomalyHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "metrics.db"
        self.detected = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-02-10"),
                    "revenue": 300.0,
                    "orders": 60.0,
                    "anomaly_score": 0.25,
                    "is_anomaly": True,
                    "explanation": "Revenue increased unusually.",
                },
                {
                    "date": pd.Timestamp("2026-02-11"),
                    "revenue": 100.0,
                    "orders": 20.0,
                    "anomaly_score": 0.05,
                    "is_anomaly": False,
                    "explanation": "",
                },
            ]
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_severity_bands(self):
        self.assertEqual(_severity(0.01), "Low")
        self.assertEqual(_severity(0.03), "Medium")
        self.assertEqual(_severity(0.10), "High")
        self.assertEqual(_severity(0.20), "Critical")

    def test_records_top_metric_drivers_and_is_idempotent(self):
        first_inserted = record_anomalies(
            self.detected,
            ["revenue", "orders"],
            "source-1",
            self.database_path,
        )
        second_inserted = record_anomalies(
            self.detected,
            ["revenue", "orders"],
            "source-1",
            self.database_path,
        )

        history = query_anomaly_history(database_path=self.database_path)
        self.assertEqual(first_inserted, 2)
        self.assertEqual(second_inserted, 0)
        self.assertEqual(len(history), 2)
        self.assertEqual(history["Date"].nunique(), 1)
        self.assertEqual(set(history["Metric"]), {"Revenue", "Orders"})
        self.assertEqual(history.iloc[0]["Severity"], "Critical")

    def test_month_filter_and_month_list(self):
        record_anomalies(
            self.detected,
            ["revenue"],
            "source-1",
            self.database_path,
        )
        april = self.detected.copy()
        april["date"] = pd.Timestamp("2026-04-01")
        record_anomalies(april, ["revenue"], "source-2", self.database_path)

        february = query_anomaly_history("2026-02", database_path=self.database_path)
        months = query_history_months(database_path=self.database_path)

        self.assertEqual(len(february), 1)
        self.assertEqual(months, ["2026-04", "2026-02"])


if __name__ == "__main__":
    unittest.main()
