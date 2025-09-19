# backend/report_generator.py
from backend.utils import get_logger
logger = get_logger(__name__)

from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # safe headless backend
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
REPORTS_DIR = ROOT / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"

def ensure_dirs():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

def _save_charts(df: pd.DataFrame) -> list:
    """
    Create simple charts for every numeric column.
    Returns list of relative chart paths (relative to reports dir).
    """
    charts = []
    nums = df.select_dtypes(include="number")
    if nums.empty:
        return charts

    for col in nums.columns:
        plt.close("all")
        fig, ax = plt.subplots()
        try:
            if pd.api.types.is_datetime64_any_dtype(df.index):
                ax.plot(df.index, df[col])
            else:
                ax.plot(range(len(df)), df[col])
            ax.set_title(col)
            ax.set_xlabel("")
            ax.set_ylabel(str(col))
            chart_name = f"{col.replace(' ', '_')}.png"
            chart_path = CHARTS_DIR / chart_name
            fig.tight_layout()
            fig.savefig(chart_path)
            charts.append(str(chart_path))  # absolute path for easier use later
            plt.close(fig)
        except Exception as e:
            logger.warning("Could not plot column %s: %s", col, e)
            plt.close(fig)
    return charts

def generate_report(df: pd.DataFrame, summary_text: str = None, report_name: str = "sample_report"):
    """
    Generate an HTML report (and attempt PDF via pdfkit, falling back to WeasyPrint).
    Returns dict with generated file paths: {'html': Path, 'pdf': Path or None, 'charts': list of Paths}
    """
    ensure_dirs()

    # basic stats and table
    try:
        stats_html = df.describe(include="all").to_html(classes="table", border=0)
    except Exception:
        stats_html = "<p>Could not generate statistics.</p>"

    table_html = df.head(50).to_html(index=False, classes="table", border=0)

    # charts
    charts = _save_charts(df)

    # render template
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report_template.jinja2")

    html_str = template.render(
        title=f"AutoPort Report — {report_name}",
        generated_on=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        summary_text=summary_text,
        stats_html=stats_html,
        table_html=table_html,
        charts=charts,
    )

    html_path = REPORTS_DIR / f"{report_name}.html"
    html_path.write_text(html_str, encoding="utf-8")
    logger.info("Wrote HTML report to %s", html_path)

    # attempt PDF (first pdfkit, then WeasyPrint fallback)
    pdf_path = REPORTS_DIR / f"{report_name}.pdf"
    try:
        import pdfkit
        pdfkit.from_file(str(html_path), str(pdf_path))
        logger.info("Wrote PDF report to %s", pdf_path)
    except Exception as e1:
        logger.warning("pdfkit failed: %s", e1)
        try:
            from weasyprint import HTML
            HTML(filename=str(html_path)).write_pdf(str(pdf_path))
            logger.info("Wrote PDF report (WeasyPrint) to %s", pdf_path)
        except Exception as e2:
            logger.error("PDF not created (both pdfkit and WeasyPrint failed): %s", e2)
            pdf_path = None

    # return paths in a dict for easier use in Phase F
    return {
        "html": html_path,
        "pdf": pdf_path,
        "charts": charts
    }
