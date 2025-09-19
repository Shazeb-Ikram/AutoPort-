# backend/summarizer.py
from typing import Optional
import pandas as pd
from backend.utils import get_logger

logger = get_logger(__name__)

def summarize_dataframe(df: pd.DataFrame, max_items: int = 3) -> str:
    """
    Produce a short rule-based summary of a dataframe.
    Kept simple and deterministic so it runs offline without AI models.
    """
    rows, cols = df.shape
    logger.info("Summarizing DataFrame: rows=%d, columns=%d", rows, cols)

    lines = [f"Rows: {rows}, Columns: {cols}."]

    # Missing values
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if not missing.empty:
        mv_str = ", ".join(f"{c} ({int(n)})" for c, n in missing.items())
        lines.append("Missing values by column: " + mv_str)
        logger.info("Missing values detected: %s", mv_str)

    # Numeric summary
    nums = df.select_dtypes(include="number")
    if not nums.empty:
        means = nums.mean().sort_values(ascending=False)
        top_col = means.index[0]
        lines.append(f"Top numeric column by mean: {top_col} (mean={means.iloc[0]:.2f})")
        logger.info("Top numeric column: %s (mean=%.2f)", top_col, means.iloc[0])

        # Include sample stats for first few numeric columns
        for c in list(nums.columns[:max_items]):
            s = nums[c].dropna()
            lines.append(f"{c}: sum={s.sum():.2f}, mean={s.mean():.2f}, min={s.min():.2f}, max={s.max():.2f}")

    # Time-aware insight if a date-like column exists
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
    if date_cols and not nums.empty:
        dc = date_cols[0]
        try:
            dt = pd.to_datetime(df[dc], errors="coerce").dropna()
            if len(dt) > 1:
                series_col = nums.columns[0]
                joined = df[[dc, series_col]].dropna()
                if len(joined) >= 2:
                    first = joined[series_col].iloc[0]
                    last = joined[series_col].iloc[-1]
                    if first != 0:
                        pct = (last - first) / abs(first) * 100
                        lines.append(f"From {joined[dc].iloc[0]} to {joined[dc].iloc[-1]}, {series_col} changed by {pct:.2f}%.")
                        logger.info("Time-based change for %s: %.2f%%", series_col, pct)
        except Exception as e:
            logger.warning("Failed to generate time-based insight for column %s: %s", dc, e)

    if len(lines) == 0:
        logger.info("No meaningful summary could be generated.")
        return "No meaningful summary could be generated."
    return "\n".join(lines)
