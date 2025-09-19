# backend/data_ingest.py
"""
Simple, robust data ingestion helpers for AutoPort (CSV, Excel, JSON, API, logs).

Usage:
    df = load_data("examples/sample.csv")
    df = load_data("examples/sample.xlsx", source_type="excel")
    df = load_data("https://jsonplaceholder.typicode.com/todos")
"""

from pathlib import Path
from typing import Optional, List
import json
import pandas as pd
import requests

from backend.utils import get_logger

# ✅ Single module-level logger
logger = get_logger(__name__)


def _infer_type(source: str, source_type: Optional[str]):
    if source_type:
        return source_type.lower()
    if str(source).startswith(("http://", "https://")):
        return "api"
    ext = Path(source).suffix.lower()
    if ext in (".csv",):
        return "csv"
    if ext in (".xls", ".xlsx"):
        return "excel"
    if ext in (".json",):
        return "json"
    if ext in (".log", ".txt"):
        return "log"
    # default fallback
    return "csv"


def load_csv(path: str, **kwargs) -> pd.DataFrame:
    logger.info("Loading CSV: %s", path)
    return pd.read_csv(path, **kwargs)


def load_excel(path: str, **kwargs) -> pd.DataFrame:
    logger.info("Loading Excel: %s", path)
    return pd.read_excel(path, engine="openpyxl", **kwargs)


def load_json(path: str, **kwargs) -> pd.DataFrame:
    logger.info("Loading JSON: %s", path)
    try:
        return pd.read_json(path, **kwargs)
    except ValueError:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.json_normalize(data)


def load_api(url: str, timeout: int = 10, **kwargs) -> pd.DataFrame:
    logger.info("Fetching API: %s", url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return pd.json_normalize(data)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return pd.json_normalize(v)
        return pd.json_normalize([data])
    return pd.DataFrame(data)


def parse_log(path: str) -> pd.DataFrame:
    logger.info("Parsing log file: %s", path)
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split()
            rows.append({"raw": ln, "parts": parts})
    return pd.DataFrame(rows)


def validate_df(df: pd.DataFrame, required_columns: Optional[List[str]] = None) -> None:
    if df is None or df.empty:
        logger.warning("DataFrame is empty.")
    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")


def load_data(
    source: str,
    source_type: Optional[str] = None,
    required_columns: Optional[List[str]] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Universal loader. source can be a file path or an HTTP(s) URL.
    - source_type: 'csv', 'excel', 'json', 'api', 'log' (optional)
    - required_columns: list of column names to validate presence
    """
    stype = _infer_type(source, source_type)
    loader_map = {
        "csv": load_csv,
        "excel": load_excel,
        "json": load_json,
        "api": load_api,
        "log": parse_log,
    }
    if stype not in loader_map:
        raise ValueError(f"Unsupported source type: {stype}")

    df = loader_map[stype](source, **kwargs)
    validate_df(df, required_columns=required_columns)
    logger.info("Loaded DataFrame: rows=%d cols=%s", len(df), list(df.columns)[:8])
    return df
