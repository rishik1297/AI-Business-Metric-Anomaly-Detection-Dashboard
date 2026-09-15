import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.anomaly_detector import detect_anomalies
from src.preprocessing import prepare_metrics
from src.sql_store import count_observations, import_frame, query_metrics


class DataQualityAndDetectionTests(unittest.TestCase):
    def _normal_frame(self, extra_rows=None):
        dates = pd.date_range("2026-01-01", periods=40, freq="D")
        frame = pd.DataFrame(
            {
                "date": dates,
                "revenue": [100 + (index % 5) * 2 for index in range(40)],
                "orders": [20 + (index % 4) for index in range(40)],
                "conversion_rate": [0.08 + (index % 3) * 0.002 for index in range(40)],
            }
        )
        if extra_rows:
            frame = pd.concat([frame, pd.DataFrame(extra_rows)], ignore_index=True)
        return frame

    def test_missing_values_are_filled_and_all_missing_rows_removed(self):
        frame = self._normal_frame(
            [
                {
                    "date": "2026-02-10",
                    "revenue": None,
                    "orders": None,
                    "conversion_rate": None,
                }
            ]
        )
        frame.loc[0, "revenue"] = None

        prepared, features, time_column = prepare_metrics(frame)

        self.assertEqual(time_column, "date")
        self.assertEqual(features, ["revenue", "orders", "conversion_rate"])
        self.assertEqual(len(prepared), 40)
        self.assertFalse(prepared[features].isna().any().any())

    def test_exact_duplicates_are_removed(self):
        frame = self._normal_frame()
        duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

        prepared, _, _ = prepare_metrics(duplicated)

        self.assertEqual(len(duplicated), 41)
        self.assertEqual(len(prepared), 40)

    def test_invalid_numeric_values_are_coerced_or_rejected_cleanly(self):
        frame = self._normal_frame()
        frame["revenue"] = frame["revenue"].astype(str)
        frame.loc[0, "revenue"] = "not-a-number"

        prepared, features, _ = prepare_metrics(frame)

        self.assertIn("revenue", features)
        self.assertFalse(prepared[features].isna().any().any())

        invalid = pd.DataFrame({"date": ["2026-01-01"], "revenue": ["unknown"]})
        with self.assertRaisesRegex(ValueError, "No usable rows remain"):
            prepare_metrics(invalid)

    def test_normal_days_produce_expected_analysis_columns(self):
        prepared, features, _ = prepare_metrics(self._normal_frame())

        detected, _ = detect_anomalies(prepared, features, contamination=0.10)

        self.assertEqual(len(detected), 40)
        self.assertTrue({"anomaly_score", "is_anomaly", "anomaly_rank"}.issubset(detected.columns))

    def test_mild_anomaly_scores_below_severe_anomaly(self):
        frame = self._normal_frame(
            [
                {"date": "2026-02-10", "revenue": 125, "orders": 25, "conversion_rate": 0.09},
                {"date": "2026-02-11", "revenue": 350, "orders": 70, "conversion_rate": 0.20},
            ]
        )
        prepared, features, _ = prepare_metrics(frame)
        detected, _ = detect_anomalies(prepared, features, contamination=0.05)

        mild_score = detected.loc[detected["date"] == "2026-02-10", "anomaly_score"].iloc[0]
        severe_score = detected.loc[detected["date"] == "2026-02-11", "anomaly_score"].iloc[0]

        self.assertGreater(severe_score, mild_score)
        self.assertTrue(detected.loc[detected["date"] == "2026-02-11", "is_anomaly"].iloc[0])

    def test_multiple_simultaneous_anomalies_receive_distinct_ranks(self):
        frame = self._normal_frame(
            [
                {"date": "2026-02-10", "revenue": 300, "orders": 60, "conversion_rate": 0.20},
                {"date": "2026-02-11", "revenue": 10, "orders": 2, "conversion_rate": 0.01},
                {"date": "2026-02-12", "revenue": 280, "orders": 5, "conversion_rate": 0.01},
            ]
        )
        prepared, features, _ = prepare_metrics(frame)
        detected, _ = detect_anomalies(prepared, features, contamination=0.10)

        anomalies = detected[detected["is_anomaly"]]

        self.assertGreaterEqual(len(anomalies), 3)
        self.assertEqual(anomalies["anomaly_rank"].nunique(), len(anomalies))

    def test_positive_anomaly_is_detected(self):
        frame = self._normal_frame(
            [{"date": "2026-02-10", "revenue": 400, "orders": 80, "conversion_rate": 0.20}]
        )
        prepared, features, _ = prepare_metrics(frame)
        detected, _ = detect_anomalies(prepared, features, contamination=0.05)

        positive = detected.loc[detected["date"] == "2026-02-10"].iloc[0]

        self.assertTrue(bool(positive["is_anomaly"]))
        self.assertGreater(positive["revenue"], prepared["revenue"].median())

    def test_sql_end_to_end_round_trip(self):
        frame = self._normal_frame()
        prepared, features, time_column = prepare_metrics(frame)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        database_path = Path(temporary.name) / "metrics.db"

        fingerprint = import_frame(prepared, time_column, "fixture.xlsx", database_path)
        loaded = query_metrics(fingerprint, database_path)
        detected, _ = detect_anomalies(loaded, features, contamination=0.10)

        self.assertEqual(count_observations(fingerprint, database_path), 120)
        self.assertEqual(len(detected), 40)
        self.assertEqual(list(loaded.columns), ["date", "revenue", "orders", "conversion_rate"])


if __name__ == "__main__":
    unittest.main()
