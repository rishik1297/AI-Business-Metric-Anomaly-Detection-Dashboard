import os
import unittest
from unittest.mock import patch

import pandas as pd

from src.ai_summary import (
    AISummaryError,
    build_anomaly_payload,
    build_overall_payload,
    generate_overall_summary,
)


class AISummaryTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            [
                {
                    "date": "2026-01-01",
                    "revenue": 100,
                    "traffic": 100,
                    "conversion_rate": 0.10,
                    "is_anomaly": False,
                    "anomaly_rank": 2,
                },
                {
                    "date": "2026-01-02",
                    "revenue": 66,
                    "traffic": 158,
                    "conversion_rate": 0.06,
                    "is_anomaly": True,
                    "anomaly_rank": 1,
                },
            ]
        )

    def test_payload_contains_signed_metric_changes(self):
        row = self.frame.iloc[1]
        payload = build_anomaly_payload(
            row, self.frame, ["revenue", "traffic", "conversion_rate"]
        )

        metrics = {metric["metric"]: metric for metric in payload["metrics"]}
        self.assertEqual(metrics["Revenue"]["change_percent"], -34.0)
        self.assertEqual(metrics["Traffic"]["change_percent"], 58.0)
        self.assertEqual(metrics["Conversion rate"]["change_percent"], -40.0)
        self.assertEqual(payload["anomaly_rank"], 1)

    def test_overall_payload_is_bounded(self):
        frame = pd.concat([self.frame] * 20, ignore_index=True)
        frame["is_anomaly"] = [index % 2 == 1 for index in frame.index]
        payload = build_overall_payload(frame, ["revenue"])

        self.assertEqual(payload["anomaly_count"], 20)
        self.assertEqual(len(payload["anomalies"]), 10)

    def test_missing_key_is_controlled_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(AISummaryError, "GROQ_API_KEY"):
                generate_overall_summary({"anomalies": []})


if __name__ == "__main__":
    unittest.main()
