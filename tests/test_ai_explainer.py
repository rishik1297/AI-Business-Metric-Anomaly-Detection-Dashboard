import unittest

import pandas as pd

from src.ai_explainer import add_explanations, explain_anomaly


class AnomalyExplanationTests(unittest.TestCase):
    def test_includes_baseline_actual_percentage_and_business_interpretation(self):
        reference = pd.DataFrame(
            [
                {"traffic": 100, "conversion_rate": 0.10, "is_anomaly": False},
                {"traffic": 100, "conversion_rate": 0.10, "is_anomaly": False},
                {"traffic": 158, "conversion_rate": 0.06, "is_anomaly": True},
            ]
        )

        explanation = explain_anomaly(
            reference.iloc[2], reference, ["traffic", "conversion_rate"]
        )

        self.assertIn("Traffic increased 58%", explanation)
        self.assertIn("normal baseline of 100.00", explanation)
        self.assertIn("actual value was 158.00", explanation)
        self.assertIn("Conversion rate decreased 40%", explanation)
        self.assertIn("deterioration in conversion performance", explanation)

    def test_limits_explanation_to_three_drivers(self):
        reference = pd.DataFrame(
            [
                {"a": 10, "b": 10, "c": 10, "d": 10, "is_anomaly": False},
                {"a": 20, "b": 20, "c": 20, "d": 20, "is_anomaly": True},
            ]
        )

        explanation = explain_anomaly(reference.iloc[1], reference, ["a", "b", "c", "d"])

        self.assertEqual(explanation.count("actual value"), 3)
        self.assertNotIn("D", explanation)

    def test_handles_zero_baseline_without_infinite_percentage(self):
        reference = pd.DataFrame(
            [
                {"revenue": 0, "is_anomaly": False},
                {"revenue": 100, "is_anomaly": True},
            ]
        )

        explanation = explain_anomaly(reference.iloc[1], reference, ["revenue"])

        self.assertIn("normal baseline of 0", explanation)
        self.assertIn("actual value was 100.00", explanation)
        self.assertNotIn("inf", explanation.lower())

    def test_normal_rows_keep_blank_explanations(self):
        frame = pd.DataFrame(
            [
                {"revenue": 10, "is_anomaly": False},
                {"revenue": 20, "is_anomaly": True},
            ]
        )

        explained = add_explanations(frame, ["revenue"])

        self.assertEqual(explained.loc[0, "explanation"], "")
        self.assertTrue(explained.loc[1, "explanation"])


if __name__ == "__main__":
    unittest.main()
