# backend/run_scheduler.py
"""
CLI to run AutoPort scheduler with notifications.

Usage:
  python -m backend.run_scheduler --test
  python -m backend.run_scheduler --interval 30
  python -m backend.run_scheduler --daily 09:00
  python -m backend.run_scheduler --once
"""

from backend.utils import setup_logging, get_logger
setup_logging()  # sets up root logging (console + logs/app.log)

import os
import argparse
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

# Import helpers
from backend.scheduler import run_report_job
from backend.notifier import notify_console, notify_email, notify_webhook

# --- Module-specific logger ---
# ensures logs/run_scheduler.log exists and logs here
logger = get_logger(__name__, log_dir="logs")
logger.info("Logging initialized for run_scheduler")

# --- CLI argument parsing ---
def parse_args():
    parser = argparse.ArgumentParser(description="Start AutoPort scheduler")
    parser.add_argument("--test", action="store_true", help="Run a 1-minute test schedule")
    parser.add_argument("--interval", type=int, help="Interval in minutes between runs")
    parser.add_argument("--daily", type=str, help="Daily time HH:MM for scheduled run")
    parser.add_argument("--once", action="store_true", help="Run the job once and exit")
    return parser.parse_args()


# --- Scheduled job wrapper ---
def scheduled_job_wrapper():
    logger.info("Scheduled job started.")
    try:
        report_paths = run_report_job()
        logger.info("Report generation complete: %s", report_paths)

        html_path = report_paths.get("html")
        report_name = html_path if html_path else "report"
        message = f"[AutoPort] Scheduled report generated: {report_name}"

        notify_console(message)

        smtp_user = os.getenv("SMTP_USER")
        if smtp_user:
            notify_email(subject=f"AutoPort Report: {report_name}", body=message, to_email=smtp_user)

        notify_webhook(message)
        logger.info("Notifications sent successfully.")
    except Exception as e:
        logger.exception("Error during scheduled job: %s", e)


# --- Main scheduler ---
def main():
    args = parse_args()
    logger.info("Starting run_scheduler (args=%s)", vars(args))

    scheduler = BlockingScheduler()

    if args.once:
        logger.info("Running a single job and exiting.")
        scheduled_job_wrapper()
        return

    if args.test:
        logger.info("Scheduling test job: every 1 minute")
        scheduler.add_job(scheduled_job_wrapper, IntervalTrigger(minutes=1), next_run_time=datetime.now())
    elif args.interval:
        logger.info("Scheduling job every %s minutes.", args.interval)
        scheduler.add_job(scheduled_job_wrapper, IntervalTrigger(minutes=args.interval), next_run_time=datetime.now())
    elif args.daily:
        try:
            hh, mm = map(int, args.daily.split(":"))
            scheduler.add_job(scheduled_job_wrapper, CronTrigger(hour=hh, minute=mm))
            logger.info("Scheduled daily at %02d:%02d", hh, mm)
        except Exception as e:
            logger.exception("Invalid --daily value, expected HH:MM. Error: %s", e)
            return
    else:
        scheduler.add_job(scheduled_job_wrapper, CronTrigger(hour=9, minute=0))
        logger.info("No scheduling args provided; defaulting to daily at 09:00")

    try:
        logger.info("Scheduler starting... (CTRL+C to stop)")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")
    except Exception as exc:
        logger.exception("Scheduler crashed: %s", exc)


if __name__ == "__main__":
    main()
