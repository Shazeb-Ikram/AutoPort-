# backend/scheduler.py
"""
Lightweight scheduler helpers for AutoPort.
Provides:
 - run_report_job(): attempt function-mode then subprocess fallback
"""
from backend.utils import get_logger
logger = get_logger(__name__)

import os
import sys
import subprocess
import importlib
from datetime import datetime

LOG_PATH = os.environ.get("AUTOPORT_SCHEDULER_LOG", "logs/scheduler.log")

def setup_logging_dirs():
    """Ensure log directories exist."""
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    logger.info("Scheduler directories ensured. Log file path: %s", LOG_PATH)

def run_demo_subprocess() -> bool:
    """Fallback: run the demo runner as a subprocess."""
    logger.info("Attempting subprocess fallback: python -m backend.run_demo")
    try:
        res = subprocess.run([sys.executable, "-m", "backend.run_demo"],
                             capture_output=True, text=True, check=False)
        logger.info("run_demo exitcode=%s", res.returncode)
        if res.stdout:
            logger.info("run_demo stdout:\n%s", res.stdout.strip())
        if res.stderr:
            logger.warning("run_demo stderr:\n%s", res.stderr.strip())
        return res.returncode == 0
    except Exception as exc:
        logger.exception("Subprocess fallback failed: %s", exc)
        return False

def try_function_mode() -> bool:
    """Try calling data loader + report generator directly."""
    try:
        di = importlib.import_module("backend.data_ingest")
        rg = importlib.import_module("backend.report_generator")
    except Exception as exc:
        logger.warning("Could not import backend modules: %s", exc)
        return False

    # Candidate function names
    load_candidates = ("load_data", "load", "read_data", "get_data")
    report_candidates = ("generate_report", "create_report", "run_report", "write_report")

    load_fn = next((getattr(di, n) for n in load_candidates if hasattr(di, n)), None)
    report_fn = next((getattr(rg, n) for n in report_candidates if hasattr(rg, n)), None)

    df = None
    if load_fn:
        logger.info("Found data loader: %s", load_fn.__name__)
        try:
            df = load_fn()
            logger.info("Data loader returned type: %s", type(df))
        except TypeError:
            try:
                df = load_fn("examples/sample.csv")
                logger.info("Data loader(sample) returned type: %s", type(df))
            except Exception as e:
                logger.warning("load_fn failed with sample path: %s", e)
        except Exception as e:
            logger.warning("load_fn raised: %s", e)

    if report_fn:
        logger.info("Found report writer: %s", report_fn.__name__)
        try:
            if df is not None:
                report_fn(df)
            else:
                report_fn()
            logger.info("Report writer ran successfully (function-mode).")
            return True
        except TypeError:
            try:
                report_fn("reports/auto_report")
                logger.info("Report writer ran with path arg.")
                return True
            except Exception as e:
                logger.exception("Report function failed with path arg: %s", e)
        except Exception as e:
            logger.exception("Report function raised an exception: %s", e)

    logger.info("Function-mode did not succeed.")
    return False

def run_report_job():
    """Main job called by the scheduler."""
    logger.info("=== Starting scheduled report job: %s ===", datetime.utcnow().isoformat())
    try:
        if try_function_mode():
            logger.info("Report generation succeeded via function-mode.")
            return {"html": "reports/sample_report.html", "pdf": "reports/sample_report.pdf", "charts": []}
        logger.info("Function-mode failed. Trying subprocess fallback...")
        if run_demo_subprocess():
            logger.info("Report generation succeeded via subprocess fallback.")
            return {"html": "reports/sample_report.html", "pdf": "reports/sample_report.pdf", "charts": []}
        logger.error("Report generation failed (both function-mode and subprocess). Check logs.")
        return {}
    except Exception as exc:
        logger.exception("Unexpected error in run_report_job: %s", exc)
        return {}
