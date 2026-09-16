# AI Business Metric Anomaly Detection Dashboard

A business analytics dashboard for identifying unusual metric changes, explaining likely drivers, and surfacing operational insights from business data.

## Live Streamlit App

[https://ai-business-metric-anomaly-detection-dashboard.streamlit.app/](https://ai-business-metric-anomaly-detection-dashboard.streamlit.app/)

## Overview

This project helps analysts and business teams detect abnormal movement in key metrics such as revenue, orders, customers, traffic, and conversion rate. The app loads business data, validates it, stores the cleaned results in SQLite, runs anomaly detection, and explains the detected issues in a business-friendly format.

## Key Features

- Excel, CSV, and XLS upload support
- Automatic data cleaning and metric normalization
- SQLite-backed observation and anomaly history storage
- Isolation Forest anomaly detection
- Ranked anomaly review by score and severity
- Explanations based on baseline and percentage change
- Optional Groq AI summary generation
- Streamlit dashboard with charts and downloads
- Power BI export support for reporting workflows

## Quick Start

### Run locally

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

After the app starts, open the local Streamlit URL shown in the terminal, usually:

```text
http://localhost:8501
```

## Run the dashboard from the repository

```bash
cd "D:\analysis project\ai analysis"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Power BI Dashboard Viewing

The dashboard exports Power BI-ready CSV files for downstream reporting.

1. Run the analysis in the Streamlit app.
2. Use the export option to generate the Power BI files.
3. Open Power BI Desktop.
4. Select Get Data > Text/CSV.
5. Import the generated files from the `reports/powerbi` folder, including:
   - `metric_observations.csv`
   - `anomaly_history.csv`
6. Refresh the data after each new analysis if you want the latest results.
7. Use the report visuals to explore trends, anomaly counts, and alert history.

This gives you a simple way to view the same output in a Power BI dashboard while keeping the analysis logic in Python and Streamlit.

## Tech Stack

- Python
- Pandas
- SQLite
- Scikit-learn
- Streamlit
- Groq API (optional)
- Power BI CSV export workflow

## Project Structure

```text
.
├── dashboard/
│   └── app.py
├── data/
├── reports/
│   └── powerbi/
├── src/
│   ├── ai_explainer.py
│   ├── ai_summary.py
│   ├── anomaly_detector.py
│   ├── data_loader.py
│   ├── email_alert.py
│   ├── preprocessing.py
│   ├── sql_store.py
│   └── __init__.py
├── tests/
├── README.md
├── requirements.txt
├── .env.example
├── .env
└── .gitignore
```

## Quick Start

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Then open the local URL shown in the terminal, typically:

```text
http://localhost:8501
```

## Power BI Dashboard Viewing

The app exports Power BI-ready CSV files for reporting.

1. Run the analysis in the Streamlit app.
2. Use the export action to generate the CSV files.
3. Open Power BI Desktop.
4. Choose Get Data > Text/CSV.
5. Import the generated files from the `reports/powerbi` folder.
6. Refresh the dataset after each new analysis.

Files typically include:

- `metric_observations.csv`
- `anomaly_history.csv`

## Environment Variables

If you want AI-generated summaries, create a local `.env` file:

```env
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

> Keep `.env` local and never commit it to source control.

## Testing

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

This project includes automated checks for anomaly detection, data quality, SQL storage, AI explanation logic, and Power BI export output.

## License

This project is intended for portfolio and business analytics demonstration use.


