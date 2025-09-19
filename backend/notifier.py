# backend/notifier.py
"""
Notifier module for AutoPort:
- notify_console(message)
- notify_email(subject, body, to_email)
- notify_webhook(message)
- notify(report_path, report_name)  <-- wrapper for run_demo/scheduler
"""

import os
import time
import smtplib
from email.message import EmailMessage

try:
    import requests
except Exception:
    requests = None

# Optional auto-load .env if python-dotenv installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ✅ Use centralized logger
from backend.utils import get_logger
logger = get_logger(__name__)


def notify_console(message: str):
    """Print message to console"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}][console] {message}")


def notify_email(subject: str, body: str, to_email: str):
    """Send email using SMTP env vars"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP_USER or SMTP_PASSWORD not set, skipping email")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        logger.info("Email sent to %s", to_email)
    except Exception as e:
        logger.error("Failed to send email: %s", e)


def notify_webhook(message: str):
    """Send message to Discord or Slack webhook"""
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logger.warning("WEBHOOK_URL not set, skipping webhook")
        return
    if requests is None:
        logger.warning("requests not installed, cannot send webhook")
        return
    payload = {"content": message} if "discord" in webhook_url else {"text": message}
    try:
        requests.post(webhook_url, json=payload, timeout=10)
        logger.info("Webhook notification sent")
    except Exception as e:
        logger.error("Failed to send webhook: %s", e)


def notify(report_path: str, report_name: str) -> list[str]:
    """
    Wrapper notification function.
    Called by run_demo.py and scheduler.
    Returns a list of messages about notifications sent.
    """
    messages = []
    msg = f"Report ready: {report_name} at {report_path}"
    logger.info(msg)

    # Always console
    notify_console(msg)
    messages.append(f"console: {msg}")

    # Optional email
    to_email = os.getenv("NOTIFY_EMAIL")
    if to_email:
        notify_email(
            subject=f"[AutoPort] Report Ready: {report_name}",
            body=msg,
            to_email=to_email
        )
        messages.append(f"email: sent to {to_email}")

    # Optional webhook
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        notify_webhook(msg)
        messages.append(f"webhook: sent to {webhook_url}")

    return messages
