# AI Business-Metric Anomaly Detection Dashboard

## Project Overview

This project is an AI-assisted business analytics dashboard that detects unusual patterns in business metrics, explains the likely drivers of each anomaly, stores observations and alert history in SQLite, and presents the results through Streamlit.

The application is designed for analysts who need to move from raw Excel reports to actionable business insight without manually reviewing every row.

## Business Problem

Business teams often receive daily or periodic reports containing revenue, orders, customers, traffic, conversion rates, and other metrics. Important changes can be difficult to find because:

- Large reports are time-consuming to review manually.
- Several metrics can change at the same time.
- A single metric may look normal while its combination with other metrics is unusual.
- Historical alerts can be difficult to track.
- Raw anomaly scores do not explain the business meaning of an event.

## Solution

The application provides an end-to-end analytics workflow:

```text
Excel/CSV report
      ↓
Python loading and validation
      ↓
SQLite normalized database
      ↓
SQL query and pandas preparation
      ↓
Anomaly detection
      ↓
Business explanations and optional Groq summaries
      ↓
Streamlit dashboard and downloadable report
```

The current implementation uses Isolation Forest for unsupervised anomaly detection. It does not require a pre-labeled dataset of normal and abnormal business days.

## Key Features

- Upload Excel, XLS, or CSV business reports.
- Use the default one-year synthetic Excel dataset.
- Normalize column names automatically.
- Detect date or period columns.
- Convert numeric-like text into numeric values.
- Handle missing and invalid metric values.
- Remove exact duplicate rows before analysis.
- Store normalized observations in SQLite.
- Prevent duplicate SQL imports using source fingerprints.
- Detect unusual business records with Isolation Forest.
- Rank anomalies by anomaly score.
- Explain anomalies using baseline, actual value, and percentage difference.
- Use friendly labels for common business metrics.
- Store anomaly history in SQLite.
- Review alerts by month with severity levels.
- Generate optional Groq AI business summaries.
- Display trends and anomaly rankings in Streamlit.
- Download a scored CSV report.
- Run automated tests for data quality, SQL, explanations, and anomaly behavior.

## Dataset

The included dataset is:

```text
data/business_metrics.xlsx
```

It contains one year of daily synthetic business data:

- 365 daily rows
- `date`
- `revenue`
- `orders`
- `customers`
- `conversion_rate`

The data includes normal variation, seasonality, random noise, and deliberately planted unusual events for testing.

After normalization, four metrics across 365 dates produce:

$$365 \\times 4 = 1{,}460$$

metric observations in SQLite.

## Synthetic Data Generation

The dataset was generated programmatically rather than entered manually. Python created:

- A daily date range covering one year.
- Weekly and annual seasonal patterns.
- Random but reproducible business variation.
- Revenue, order, customer, and conversion-rate metrics.
- Controlled positive and negative anomaly events.

A fixed random seed makes the dataset reproducible. This allows the same test data to be regenerated and makes model behavior easier to compare.

## Data Processing

The processing pipeline is implemented across the data loader and preprocessing modules.

1. Read Excel or CSV data with pandas.
2. Normalize column names to lowercase underscore format.
3. Identify a date, datetime, timestamp, time, or period column.
4. Remove exact duplicate rows.
5. Convert metric-like values to numeric values.
6. Convert invalid values and infinities to missing values.
7. Remove rows where every metric is unusable.
8. Fill remaining missing numeric values with column medians.
9. Validate that enough rows and numeric metrics remain.
10. Import the cleaned data into SQLite.
11. Query the selected source back into a wide pandas DataFrame.

The application requires a valid date or period column for SQL-backed analysis and historical review.

## Anomaly Detection Methodology

The project uses **Isolation Forest** from scikit-learn.

Isolation Forest is an unsupervised algorithm. It repeatedly creates random partitions of the data. Unusual records are isolated in fewer partitions than normal records, so they receive higher anomaly scores.

The detector produces:

- `anomaly_score`
- `is_anomaly`
- `anomaly_rank`

The dashboard includes an **Expected anomaly rate** slider called contamination. Contamination is the expected proportion of rows that should be treated as anomalies.

For 365 rows:

- `0.01` is approximately 4 rows.
- `0.05` is approximately 18 to 19 rows.
- `0.10` is approximately 36 to 37 rows.

A lower value flags only the most unusual rows. A higher value flags more rows for investigation. It is a threshold-setting assumption, not proof that a row is truly wrong.

## Anomaly Explanation

The deterministic explanation layer compares each anomalous row with the mean values of normal rows.

Each explanation can contain:

```text
Normal baseline → Actual value → Percentage difference → Business interpretation
```

Example structure:

> Revenue increased 87% compared with the normal baseline of 51,959.15; actual value was 97,172.78. This combination indicates an unusual increase in business activity.

Common metric aliases include:

- `revenue` and `sales` → Revenue or Sales
- `traffic`, `visitors`, and `sessions` → Traffic
- `conversion` and `conversion_rate` → Conversion rate
- `orders` → Orders
- `customers` → Customers

Unknown columns receive a humanized version of their column name.

## AI/LLM Component

The project includes an optional Groq integration for higher-level business summaries.

The AI layer receives structured facts such as:

```text
Revenue: -34%
Traffic: +58%
Conversion rate: -40%
Refunds: +120%
```

It can generate:

- One overall business summary.
- Per-anomaly summaries for the highest-ranked anomalies.

The prompt instructs the model to use only supplied metric facts and describe possible causes as hypotheses rather than proven facts.

The application uses:

```text
GROQ_API_KEY
GROQ_MODEL=openai/gpt-oss-120b
```

Create a root `.env` file locally, never commit it, and never place an API key in source code:

```env
GROQ_API_KEY=your-new-groq-key
GROQ_MODEL=openai/gpt-oss-120b
```

If the key is missing or the request fails, deterministic anomaly detection remains available and the dashboard displays an AI-specific error.

## Dashboard

The Streamlit dashboard provides:

- Detection settings sidebar.
- Excel, XLS, and CSV upload control.
- Rows analyzed metric.
- Anomalies detected metric.
- Metrics used metric.
- SQL observation count and source name.
- Anomaly ranking table.
- Full business explanations.
- Monthly anomaly history review.
- Severity labels: Low, Medium, High, and Critical.
- Metric trend charts.
- Optional Groq AI summary section.
- Downloadable scored CSV report.
- Power BI export for metric observations and anomaly history.

The anomaly history section counts distinct anomaly dates for the selected month and displays:

```text
Date | Metric | Score | Severity | Alert
```

One anomaly date can produce multiple history rows because the top metric drivers are stored separately.

## Power BI Integration

SQLite remains the source of truth, and the dashboard can export Power BI-ready CSV snapshots from the database:

```text
reports/powerbi/metric_observations.csv
reports/powerbi/anomaly_history.csv
```

Use the **Export data for Power BI** button in the dashboard. It creates both files and provides download buttons.

In Power BI Desktop, select **Get data → Text/CSV** for each file. Refresh the CSV files after running a new analysis, then select **Refresh** in Power BI. Generated exports are ignored by Git through `reports/powerbi/*.csv`.

### Completed Power BI Report

The Power BI report has been created and saved in the project `reports` folder. It includes:

- `Business Metrics Over Time` line chart.
- `Total Anomalies` card.
- Date slicer for filtering the report period.
- `Anomaly Review` table with Date, Metric, Score, Severity, and Alert.
- `Anomalies by Severity` chart.
- Professional report title and subtitle.

The Power BI report uses the exported SQLite snapshots as its data source. The report can be refreshed after generating new CSV exports from the Streamlit dashboard.

## Project Architecture

```text
Input report
    ↓
load_metrics()
    ↓
prepare_metrics()
    ↓
SQLite metric_observations table
    ↓
query_metrics()
    ↓
detect_anomalies()
    ↓
add_explanations()
    ├── record_anomalies() → SQLite anomaly_history table
    ├── Groq AI summaries
    └── Streamlit dashboard and CSV download
```

## Tech Stack

- Python 3.13
- pandas
- NumPy through the data-generation workflow
- openpyxl
- scikit-learn
- Streamlit
- SQLite through Python's built-in `sqlite3` library
- Groq Python SDK
- Python `unittest`

## Project Structure

```text
ai analysis/
├── .env                         # Local secrets; never commit
├── .gitignore
├── README.md
├── requirements.txt
├── dashboard/
│   └── app.py                   # Streamlit entry point
├── data/
│   └── business_metrics.xlsx    # Default synthetic input
├── reports/
│   ├── .gitkeep
│   ├── metrics.db               # Local SQLite database
│   └── test_results.md          # Documented test results
├── src/
│   ├── ai_explainer.py          # Deterministic explanations
│   ├── ai_summary.py            # Groq integration
│   ├── anomaly_detector.py      # Isolation Forest
│   ├── data_loader.py           # Excel/CSV loading
│   ├── email_alert.py           # Optional SMTP alert module
│   ├── preprocessing.py         # Cleaning and validation
│   └── sql_store.py             # SQLite storage and history
└── tests/
    ├── test_ai_explainer.py
    ├── test_ai_summary.py
    ├── test_anomaly_history.py
    ├── test_data_quality_and_detection.py
    ├── test_powerbi_export.py
    └── test_sql_store.py
```

## Installation

Open PowerShell in the project folder:

```powershell
cd "D:\analysis project\ai analysis"
```

Create a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## How to Run

From the project root:

```powershell
python -m streamlit run dashboard\app.py
```

Open the local URL printed by Streamlit, normally:

```text
http://localhost:8501
```

If that port is already in use, Streamlit selects another available port.

To use Groq summaries, configure `.env` or the terminal environment before starting Streamlit. Keep the terminal running while using the dashboard.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```

The current test suite contains 23 passing tests covering explanations, Groq payload validation, data quality, SQL storage, anomaly history, Power BI exports, and anomaly scenarios.

## Example Output

For an anomalous business day, the deterministic explanation can look like:

```text
Revenue increased 87% compared with the normal baseline of 51,959.15;
actual value was 97,172.78; Orders decreased 34% compared with the normal
baseline of 1,046.64; actual value was 694.00. This combination indicates
an unusual deterioration in business performance.
```

The dashboard also displays:

```text
Rows analyzed: 365
Anomalies: 19
Metrics used: 4
SQL observations: 1,460
```

## Results & Model Evaluation

The current synthetic dataset and SQL-backed pipeline have been verified with:

- 365 daily input rows.
- 1,460 normalized SQL observations.
- 19 detected anomaly rows at the default contamination setting.
- Four metric columns.
- Matching anomaly dates and labels between direct Excel and SQL-backed analysis.
- Duplicate-safe SQL imports.
- Data-quality tests for missing, invalid, duplicate, normal, mild, severe, simultaneous, and positive anomaly cases.
- Power BI export tests for both CSV files, schemas, and row counts.
- 23 automated tests passing.

The test report is available at [reports/test_results.md](reports/test_results.md).

Isolation Forest is unsupervised, so evaluation currently focuses on reproducibility, ranking behavior, controlled synthetic anomalies, data-quality handling, and parity between Excel and SQL paths. A production evaluation should use analyst-reviewed labels and business impact metrics.

## Business Value

The project can help an analyst:

- Find unusual business days faster.
- Prioritize high-scoring alerts.
- Understand which metrics drove an alert.
- Compare actual values with normal baselines.
- Investigate conversion or monetization deterioration.
- Review prior alerts by month.
- Reduce repetitive manual spreadsheet inspection.
- Produce a shareable scored report.

## Limitations

- The included dataset is synthetic and should not be treated as production evidence.
- Isolation Forest scores are relative to the current dataset and settings.
- Contamination is an analyst-selected assumption.
- A valid date or period column is required for SQL-backed analysis.
- Very small datasets may not provide reliable anomaly patterns.
- AI summaries depend on Groq availability, API credentials, model behavior, and network access.
- AI explanations are interpretations, not proof of root cause.
- Local SQLite is appropriate for this single-workspace application but is not a multi-user production database.
- The current history identity is based on source fingerprint, date, and metric.

## Future Improvements

- Add a fingerprint-aware automatic AI-summary refresh when the dataset or detection settings change.
- Add configurable anomaly severity thresholds.
- Add analyst feedback such as confirmed, dismissed, or investigated.
- Add a production PostgreSQL option for multi-user deployments.
- Add scheduled report ingestion.
- Add email or messaging notifications for new severe alerts.
- Add role-based access and authentication.
- Add richer time-series and seasonal baselines.
- Add precision, recall, and analyst-agreement evaluation using labeled production data.
- Add a deployment pipeline and public hosted demo.

## Demo

### Local demo

Run:

```powershell
python -m streamlit run dashboard\app.py
```

Then open the local URL printed by Streamlit.

### Temporary public demo

For a temporary public URL, start Streamlit on a reachable local port and use a tunnel such as Cloudflare Tunnel:

```powershell
python -m streamlit run dashboard\app.py --server.address 0.0.0.0 --server.port 8505
```

In another terminal:

```powershell
cloudflared tunnel --url http://localhost:8505
```

Cloudflare will print a temporary HTTPS URL. Keep both terminals open. Do not expose `.env`, API keys, or sensitive business data. No permanent public deployment URL is configured for this repository yet.

## Author

**Rishik Yamasani**


