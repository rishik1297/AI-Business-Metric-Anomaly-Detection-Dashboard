import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.sql_store import (
    count_observations,
    import_frame,
    initialize_database,
    query_metrics,
)


class SqlStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "metrics.db"
        self.frame = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                "revenue": [100.0, 110.0],
                "orders": [10.0, 11.0],
            }
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_import_and_query_round_trip(self):
        fingerprint = import_frame(
            self.frame, "date", "business_metrics.xlsx", self.database_path
        )

        loaded = query_metrics(fingerprint, self.database_path)

        self.assertEqual(count_observations(fingerprint, self.database_path), 4)
        self.assertEqual(list(loaded.columns), ["date", "revenue", "orders"])
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded.loc[0, "revenue"], 100.0)

    def test_reimport_is_idempotent(self):
        first_fingerprint = import_frame(
            self.frame, "date", "business_metrics.xlsx", self.database_path
        )
        second_fingerprint = import_frame(
            self.frame, "date", "business_metrics.xlsx", self.database_path
        )

        self.assertEqual(first_fingerprint, second_fingerprint)
        self.assertEqual(count_observations(database_path=self.database_path), 4)

    def test_missing_date_column_is_rejected(self):
        initialize_database(self.database_path)

        with self.assertRaisesRegex(ValueError, "date or period"):
            import_frame(
                self.frame.drop(columns=["date"]),
                None,
                "metrics.csv",
                self.database_path,
            )


if __name__ == "__main__":
    unittest.main()
