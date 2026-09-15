"""Optional email notifications for newly detected anomalies."""

import os
import smtplib
from email.message import EmailMessage

import pandas as pd


def send_alert(anomalies: pd.DataFrame, subject: str = "Business metric anomaly detected") -> None:
    """Send anomaly details using SMTP environment variables."""
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "ALERT_FROM", "ALERT_TO"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing SMTP configuration: {', '.join(missing)}")
    body = anomalies.to_string(index=False)
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ["ALERT_FROM"]
    message["To"] = os.environ["ALERT_TO"]
    message.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as server:
        server.starttls()
        server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        server.send_message(message)
