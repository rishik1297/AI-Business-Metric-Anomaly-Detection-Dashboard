"""Generate concise, deterministic explanations for detected anomalies."""

import re

import pandas as pd


METRIC_METADATA = {
    "revenue": {"label": "Revenue", "role": "revenue"},
    "sales": {"label": "Sales", "role": "revenue"},
    "traffic": {"label": "Traffic", "role": "traffic"},
    "visitors": {"label": "Traffic", "role": "traffic"},
    "sessions": {"label": "Traffic", "role": "traffic"},
    "orders": {"label": "Orders", "role": "orders"},
    "customers": {"label": "Customers", "role": "customers"},
    "conversion": {"label": "Conversion rate", "role": "conversion"},
    "conversion_rate": {"label": "Conversion rate", "role": "conversion"},
}


def _metric_metadata(column: str) -> dict[str, str]:
    normalized = re.sub(r"[^a-z0-9]+", "_", column.lower()).strip("_")
    metadata = METRIC_METADATA.get(normalized)
    if metadata:
        return metadata
    return {
        "label": normalized.replace("_", " ").title(),
        "role": "other",
    }


def _format_value(value: float, role: str) -> str:
    if role == "conversion":
        return f"{value * 100:,.2f}%"
    return f"{value:,.2f}"


def _format_driver(column: str, actual: float, baseline: float) -> tuple[str, str, float | None, str]:
    metadata = _metric_metadata(column)
    label = metadata["label"]
    role = metadata["role"]
    direction = "increased" if actual >= baseline else "decreased"
    if baseline == 0:
        detail = (
            f"{label} {direction} from a normal baseline of 0; "
            f"actual value was {_format_value(actual, role)}"
        )
        return detail, direction, None, role

    difference = (actual - baseline) / abs(baseline) * 100
    detail = (
        f"{label} {direction} {abs(difference):.0f}% compared with the normal "
        f"baseline of {_format_value(baseline, role)}; actual value was "
        f"{_format_value(actual, role)}"
    )
    return detail, direction, difference, role


def _interpretation(drivers: list[tuple[str, str]]) -> str:
    roles = {role: direction for role, direction in drivers}
    if roles.get("traffic") == "increased" and roles.get("conversion") == "decreased":
        return "This combination indicates an unusual deterioration in conversion performance."
    if roles.get("revenue") == "decreased" and roles.get("traffic") == "increased":
        return "This combination indicates weak monetization despite increased traffic."
    if roles.get("revenue") == "increased" and roles.get("orders") == "increased":
        return "This combination indicates an unusual increase in business demand."
    if any(direction == "decreased" for _, direction in drivers):
        return "This combination indicates an unusual deterioration in business performance."
    return "This combination indicates an unusual increase in business activity."


def explain_anomaly(row: pd.Series, reference: pd.DataFrame, feature_columns: list[str]) -> str:
    """Describe the top metric deviations with business context."""
    normal = reference.loc[~reference["is_anomaly"], feature_columns]
    baseline = normal if not normal.empty else reference[feature_columns]
    means = baseline.mean()
    deviations = (row[feature_columns] - means).abs().sort_values(ascending=False)
    details = []
    driver_roles = []
    for column in deviations.head(3).index:
        detail, direction, _, role = _format_driver(column, row[column], means[column])
        details.append(detail)
        driver_roles.append((role, direction))
    if not details:
        return "The row differs from the learned business-metric pattern."
    return "; ".join(details) + ". " + _interpretation(driver_roles)


def add_explanations(frame: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    """Append an explanation to each row, leaving normal rows blank."""
    result = frame.copy()
    result["explanation"] = ""
    for index, row in result[result["is_anomaly"]].iterrows():
        result.at[index, "explanation"] = explain_anomaly(row, result, feature_columns)
    return result
