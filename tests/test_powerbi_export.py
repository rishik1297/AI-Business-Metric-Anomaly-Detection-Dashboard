import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.preprocessing import prepare_metrics
from src.sql_store import (
    export_anomaly_history,
    export_metric_observations,
    import_frame,
    record_anomalies,
)


class PowerBIExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "metrics.db"
        self.export_directory = Path(self.temporary_directory.name) / "powerbi"
        frame = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=3),
                "revenue": [100.0, 110.0, 300.0],
                "orders": [10.0, 11.0, 30.0],
            }
        )
        self.prepared, self.features, self.time_column = prepare_metrics(frame)
        self.fingerprint = import_frame(
            self.prepared,
            self.time_column,
            "fixture.xlsx",
            self.database_path,
        )
        detected = self.prepared.copy()
        detected["anomaly_score"] = [0.01, 0.02, 0.25]
        detected["is_anomaly"] = [False, False, True]
        detected["explanation"] = ["", "", "Revenue increased unusually."]
        record_anomalies(
            detected,
            self.features,
            self.fingerprint,
            self.database_path,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_exports_metric_observations_csv(self):
        output_path = export_metric_observations(
            self.database_path, self.export_directory
        )

        exported = pd.read_csv(output_path)

        self.assertEqual(output_path.name, "metric_observations.csv")
        self.assertEqual(len(exported), 6)
        self.assertEqual(
            list(exported.columns),
            [
                "observation_date",
                "metric_name",
                "metric_position",
                "metric_value",
                "source_name",
                "source_fingerprint",
                "loaded_at",
            ],
        )

    def test_exports_anomaly_history_csv(self):
        output_path = export_anomaly_history(self.database_path, self.export_directory)

        exported = pd.read_csv(output_path)

        self.assertEqual(output_path.name, "anomaly_history.csv")
        self.assertEqual(len(exported), 2)
        self.assertEqual(
            list(exported.columns), ["Date", "Metric", "Score", "Severity", "Alert"]
        )
        self.assertEqual(exported.iloc[0]["Severity"], "Critical")


if __name__ == "__main__":
    unittest.main()
