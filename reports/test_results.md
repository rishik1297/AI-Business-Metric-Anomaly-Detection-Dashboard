# Application Test Results

**Test date:** 2026-09-14
**Test command:** `python -m unittest discover -s tests -v`
**Result:** 23 tests passed

## Scenario Matrix

| Scenario | Input | Expected behavior | Actual result | Status |
|---|---|---|---|---|
| Missing values | Partial missing metric values and one row with all metrics missing | Fill usable missing values with column medians; remove rows with no usable metrics | Partial values were median-filled; all-metric-missing row was removed | PASS |
| Duplicate rows | One exact duplicate business-metric row | Keep one copy before SQL import and detection | Duplicate was removed; SQL import remains idempotent | PASS |
| Invalid data | Numeric strings plus an invalid value such as `not-a-number` | Coerce numeric strings; convert invalid values to missing; clean or reject if no usable rows remain | Numeric strings were converted; invalid value was cleaned; entirely invalid input raised a controlled `ValueError` | PASS |
| Normal days | 40 stable but slightly varying daily observations | Produce valid scores, labels, and ranks without crashing | Analysis produced all expected output columns | PASS |
| Mild anomaly | Small controlled increase in metrics | Score below a severe anomaly in the same fixture | Mild score was lower than severe score | PASS |
| Severe anomaly | Large controlled increase in metrics | Rank highly and be labeled anomalous | Severe anomaly ranked above the mild case and was labeled anomalous | PASS |
| Multiple simultaneous anomalies | Three different anomalous dates with different metric patterns | Detect multiple rows with distinct ranks | At least three anomalies were detected and ranks were unique | PASS |
| Positive anomaly | Unusually high revenue, orders, and conversion rate | Detect increase-side anomaly and preserve positive values | Positive anomaly was detected and exceeded the normal revenue median | PASS |
| SQL end to end | Cleaned 40-row fixture loaded into temporary SQLite | Store 120 metric observations, query back to wide data, and detect anomalies | 120 observations, 40 dates, correct column order, and successful detection | PASS |

## Existing Dataset Verification

The generated workbook `data/business_metrics.xlsx` was also verified through the SQL-backed path:

- 365 daily rows
- 4 numeric metrics
- 1,460 SQL observations
- 19 detected anomalies
- SQL and direct Excel pipelines produced matching anomaly dates and labels

## Interpretation

The application now has explicit behavior for the requested data-quality and anomaly scenarios. Exact duplicates are removed before analysis. Numeric-like text is converted to numbers, invalid values become missing, and median filling is used when a usable value remains. A dataset with no usable metric rows raises a controlled validation error.

Mild and severe anomaly comparisons are relative to the same fixture. Isolation Forest scores should not be treated as universal severity thresholds across unrelated datasets.

## Known Limitations

- The current tests do not make live Groq API calls; AI summaries are tested separately without network access.
- Inputs loaded into SQL require a valid date or period column.

## Anomaly History Verification

The SQLite-backed anomaly history feature was added after the original scenario run.

- Alerts are stored in the `anomaly_history` table.
- Each anomalous date stores up to three metric-driver rows.
- Severity bands are `Low`, `Medium`, `High`, and `Critical`.
- Reprocessing the same source is idempotent and does not create duplicate alerts.
- The dashboard counts distinct anomaly dates for the selected month.
- The review table displays Date, Metric, Score, Severity, and Alert.
- Focused history tests: 3 passed.

## Power BI Export Verification

- `metric_observations.csv` export passed with the expected normalized columns and row count.
- `anomaly_history.csv` export passed with Date, Metric, Score, Severity, and Alert columns.
- Power BI export tests: 2 passed.
