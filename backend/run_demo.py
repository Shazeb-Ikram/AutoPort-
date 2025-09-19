from backend.utils import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)
logger.info("Logging initialized for run_demo")

# backend/run_demo.py
import logging
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  

# logging
from backend.utils import setup_logging, get_logger
setup_logging()
log = get_logger("run_demo")


try:
    from .data_ingest import load_data
    from .report_generator import generate_report
    from .summarizer import summarize_dataframe
except Exception:
    from backend.data_ingest import load_data
    from backend.report_generator import generate_report
    from backend.summarizer import summarize_dataframe

# ✅ Always import notify separately so it’s available
from backend.notifier import notify


def main():
    print("=== run_demo.py started ===")

    ROOT = Path(__file__).resolve().parent.parent
    sample_csv = ROOT / "examples" / "sample.csv"
    print(f"Checking sample CSV at {sample_csv}")

    if not sample_csv.exists():
        raise FileNotFoundError(f"Could not find {sample_csv}")

    # Load data
    try:
        df = load_data(str(sample_csv))
        print("Data loaded using data_ingest.load_data")
    except Exception as e:
        print(f"data_ingest.load_data failed: {e}, falling back to pandas.read_csv")
        df = pd.read_csv(sample_csv)
        print("Data loaded using pandas.read_csv")

    # Summarize dataframe
    summary = summarize_dataframe(df)
    print("Data summary completed")

    # Generate report
    report_paths = generate_report(df, summary_text=summary, report_name="sample_report")
    html_path = str(report_paths["html"])
    pdf_path = str(report_paths["pdf"]) if report_paths["pdf"] else None

    log.info("Report generated: HTML=%s PDF=%s", html_path, pdf_path)

    # Send notifications
    errors = notify(report_path=html_path, report_name="sample_report")
    if errors:
        print("Notification errors:", errors)

    print("=== run_demo.py finished ===")


if __name__ == "__main__":
    main()
