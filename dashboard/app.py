"""Streamlit dashboard for business metric anomaly detection."""

import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai_explainer import add_explanations
from src.anomaly_detector import detect_anomalies
from src.data_loader import DEFAULT_DATA_PATH, infer_time_column, load_metrics
from src.preprocessing import prepare_metrics
from src.sql_store import (
    count_observations,
    export_anomaly_history,
    export_metric_observations,
    import_frame,
    query_anomaly_history,
    query_history_months,
    query_metrics,
    record_anomalies,
)
from src.ai_summary import (
    AISummaryError,
    build_anomaly_payload,
    build_overall_payload,
    generate_anomaly_summary,
    generate_overall_summary,
)


st.set_page_config(page_title="AI Anomaly Agent", page_icon="!", layout="wide")
st.title("AI Anomaly Agent")
st.caption("Detect unusual business metrics and understand which values drove the alert.")

with st.sidebar:
    st.header("Detection settings")
    contamination = st.slider("Expected anomaly rate", 0.01, 0.50, 0.05, 0.01)
    uploaded_file = st.file_uploader("Upload metrics", type=["xlsx", "xls", "csv"])

try:
    if uploaded_file:
        temporary_path = Path(".streamlit_uploaded_metrics")
        temporary_path.write_bytes(uploaded_file.getvalue())
        if uploaded_file.name.lower().endswith(".csv"):
            temporary_path = temporary_path.with_suffix(".csv")
        else:
            temporary_path = temporary_path.with_suffix(".xlsx")
        frame = load_metrics(temporary_path)
        source_name = uploaded_file.name
    else:
        frame = load_metrics(DEFAULT_DATA_PATH)
        source_name = DEFAULT_DATA_PATH.name
    frame = frame.drop_duplicates().reset_index(drop=True)
    cleaned_frame, _, source_time_column = prepare_metrics(frame)
    source_fingerprint = import_frame(cleaned_frame, source_time_column, source_name)
    sql_frame = query_metrics(source_fingerprint)
    prepared, feature_columns, time_column = prepare_metrics(sql_frame)
    detected, _ = detect_anomalies(prepared, feature_columns, contamination)
    detected = add_explanations(detected, feature_columns)
    record_anomalies(detected, feature_columns, source_fingerprint)
except Exception as error:
    st.error(str(error))
    st.info("Add rows with a date or period column and at least one numeric metric to continue.")
    st.stop()

anomaly_count = int(detected["is_anomaly"].sum())
first, second, third = st.columns(3)
first.metric("Rows analyzed", len(detected))
second.metric("Anomalies", anomaly_count)
third.metric("Metrics used", len(feature_columns))
st.sidebar.caption(f"SQL-backed observations: {count_observations(source_fingerprint):,}")
st.sidebar.caption(f"Source: {source_name}")

st.subheader("Anomaly history")
history_months = query_history_months()
current_month = date.today().strftime("%Y-%m")
month_options = sorted(set(history_months + [current_month]), reverse=True)
selected_month = st.selectbox("Review month", month_options)
history = query_anomaly_history(month=selected_month)
history_event_count = history["Date"].nunique() if not history.empty else 0
st.metric("Anomalies detected this month", int(history_event_count))
if history.empty:
    st.info("No anomaly history is available for this month.")
else:
    st.dataframe(
        history,
        width="stretch",
        hide_index=True,
        column_config={
            "Score": st.column_config.NumberColumn(format="%.4f"),
            "Alert": st.column_config.TextColumn(width="large"),
        },
    )

st.subheader("Power BI export")
st.caption("Export the current SQLite tables as CSV snapshots for Power BI Desktop.")
if st.button("Export data for Power BI"):
    metric_export = export_metric_observations()
    history_export = export_anomaly_history()
    st.success("Power BI export completed successfully.")
    st.download_button(
        "Download metric observations CSV",
        metric_export.read_bytes(),
        file_name=metric_export.name,
        mime="text/csv",
    )
    st.download_button(
        "Download anomaly history CSV",
        history_export.read_bytes(),
        file_name=history_export.name,
        mime="text/csv",
    )

st.subheader("Anomaly ranking")
display_columns = ([time_column] if time_column else []) + feature_columns + ["anomaly_score", "is_anomaly", "explanation"]
st.dataframe(
    detected[display_columns],
    width="stretch",
    hide_index=True,
    column_config={
        "explanation": st.column_config.TextColumn(
            "Business explanation",
            width="large",
        )
    },
)

st.subheader("AI business summaries")
st.caption("Generate a concise business interpretation using Groq from the detected metric changes.")
if st.button("Generate AI summaries", type="primary"):
    try:
        overall_payload = build_overall_payload(detected, feature_columns)
        overall_summary = generate_overall_summary(overall_payload)
        anomaly_summaries = {}
        for index, row in detected[detected["is_anomaly"]].head(10).iterrows():
            anomaly_summaries[index] = generate_anomaly_summary(
                build_anomaly_payload(row, detected, feature_columns)
            )
        st.session_state["ai_overall_summary"] = overall_summary
        st.session_state["ai_anomaly_summaries"] = anomaly_summaries
        st.session_state.pop("ai_summary_error", None)
    except AISummaryError as error:
        st.session_state["ai_summary_error"] = str(error)
        st.session_state.pop("ai_overall_summary", None)
        st.session_state.pop("ai_anomaly_summaries", None)

if "ai_summary_error" in st.session_state:
    st.error(st.session_state["ai_summary_error"])
elif "ai_overall_summary" in st.session_state:
    st.markdown("**Overall business summary**")
    st.write(st.session_state["ai_overall_summary"])
    st.markdown("**Per-anomaly summaries**")
    anomaly_summaries = st.session_state.get("ai_anomaly_summaries", {})
    for index, summary in anomaly_summaries.items():
        anomaly_row = detected.loc[index]
        label = anomaly_row.get("date", f"Anomaly rank {anomaly_row.get('anomaly_rank', index)}")
        with st.expander(str(label)):
            st.write(summary)

st.subheader("Metric trends")
chart_frame = detected.copy()
if time_column:
    chart_frame = chart_frame.set_index(time_column)
st.line_chart(chart_frame[feature_columns])

st.download_button(
    "Download scored report",
    detected.to_csv(index=False).encode("utf-8"),
    file_name="anomaly_report.csv",
    mime="text/csv",
)
