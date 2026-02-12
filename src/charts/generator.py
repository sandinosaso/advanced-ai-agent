"""
Chart generator - produces SVG charts from structured query results.

Used when the user asks to visualize or chart data (e.g. "show me a bar chart of X").
Returns a ChartSpec (type, title, x_key, y_key, svg, meta) for BFF/UI flexibility.
"""

import sys
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from . import colors as chart_colors

# Resolve once at import so we know which Python the process uses
_CHART_DEPS_AVAILABLE: Optional[bool] = None


def _check_chart_deps() -> bool:
    """Return True if matplotlib and seaborn are importable in this process."""
    global _CHART_DEPS_AVAILABLE
    if _CHART_DEPS_AVAILABLE is not None:
        return _CHART_DEPS_AVAILABLE
    try:
        import matplotlib  # noqa: F401
        import seaborn  # noqa: F401
        _CHART_DEPS_AVAILABLE = True
    except ImportError:
        _CHART_DEPS_AVAILABLE = False
    return _CHART_DEPS_AVAILABLE

# Max rows to chart (avoid huge SVGs and slow renders)
MAX_CHART_ROWS = 50
# Max SVG size in chars (sanity cap)
MAX_SVG_LENGTH = 500_000

# ChartSpec: type, title, x_key, y_key, svg, meta (rows_used, truncated)
ChartSpec = Dict[str, Any]


def _infer_chart_type(question: str) -> str:
    """Infer chart type from question keywords. Returns 'pie', 'line', or 'bar'."""
    q = question.lower()
    if any(k in q for k in ("pie", "pie chart", "proportion", "breakdown", "share of", "as a pie")):
        return "pie"
    if any(k in q for k in (
        "line", "line chart", "line graph",
        "over time", "trend", "by date", "time series", "as a line",
    )):
        return "line"
    if any(k in q for k in ("bar", "bar chart", "bar graph", "by status", "by type", "by ")):
        return "bar"
    if any(k in q for k in ("chart", "graph", "visualize", "visualization", "plot")):
        return "bar"
    return "bar"


def _is_numeric(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.replace(",", "").strip())
            return True
        except (ValueError, TypeError):
            pass
    return False


def _is_date_like(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        # Common date patterns
        s = value.strip()
        if len(s) >= 8 and ("-" in s or "/" in s):
            return True
    return False


def _classify_columns(
    data: List[Dict[str, Any]]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Return (categorical_key, numeric_key, date_key) for chart axes.
    Prefer first categorical, first numeric, first date-like column.
    """
    if not data or not isinstance(data[0], dict):
        return None, None, None
    keys = list(data[0].keys())
    cat_key = None
    num_key = None
    date_key = None
    for k in keys:
        values = [row.get(k) for row in data[:100] if k in row]
        if not values:
            continue
        if all(_is_numeric(v) for v in values if v is not None):
            if num_key is None:
                num_key = k
        elif all(_is_date_like(v) for v in values if v is not None):
            if date_key is None:
                date_key = k
        else:
            if cat_key is None:
                cat_key = k
    return cat_key, num_key, date_key


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except (ValueError, TypeError):
            pass
    return 0.0


def _cubic_spline_smooth(x: "np.ndarray", y: "np.ndarray", x_eval: "np.ndarray") -> "np.ndarray":
    """
    Natural cubic spline interpolation. Returns y values at x_eval.
    x, y are 1d arrays (length n); x_eval is 1d array of query points.
    Uses numpy only (no scipy). Second derivatives M at knots from tridiagonal system.
    """
    import numpy as np

    n = len(x)
    h = np.diff(x)
    if np.any(h <= 0):
        return np.interp(x_eval, x, y)
    d = np.diff(y) / h  # (y[i+1]-y[i])/h[i]
    # Natural spline: M[0]=M[n-1]=0. Tridiagonal: h[i-1]*M[i-1] + 2(h[i-1]+h[i])*M[i] + h[i]*M[i+1] = 6*(d[i]-d[i-1])
    A = np.zeros((n, n))
    A[0, 0] = 1
    A[-1, -1] = 1
    rhs = np.zeros(n)
    for i in range(1, n - 1):
        A[i, i - 1] = h[i - 1]
        A[i, i] = 2.0 * (h[i - 1] + h[i])
        A[i, i + 1] = h[i]
        rhs[i] = 6.0 * (d[i] - d[i - 1])
    M = np.linalg.solve(A, rhs)
    # On [x_i, x_{i+1}]: p(t)=a + b*t + c*t^2 + d*t^3, t=(x-x_i)/h_i
    # a=y_i, b=(y_{i+1}-y_i)/h_i - (2*M_i+M_{i+1})*h_i/6, c=M_i/2, d=(M_{i+1}-M_i)/(6*h_i)
    out = np.empty_like(x_eval)
    for k, xe in enumerate(x_eval):
        i = int(np.searchsorted(x, xe, side="right") - 1)
        i = max(0, min(i, n - 2))
        t = (xe - x[i]) / h[i]
        a = y[i]
        b = (y[i + 1] - y[i]) / h[i] - (2.0 * M[i] + M[i + 1]) * h[i] / 6.0
        c = M[i] / 2.0
        d_co = (M[i + 1] - M[i]) / (6.0 * h[i])
        out[k] = a + b * t + c * t**2 + d_co * t**3
    return out


def generate_chart(data: List[Dict[str, Any]], question: str) -> Optional[ChartSpec]:
    """
    Generate an SVG chart from structured query result data.

    Chart type is inferred from question keywords (pie, line, bar).
    Uses first categorical + first numeric column for bar/pie; date + numeric for line.
    Returns a ChartSpec (type, title, x_key, y_key, svg, meta) or None.

    Args:
        data: List of dicts (e.g. from SQL structured_result).
        question: User question (used for chart type and title).

    Returns:
        ChartSpec dict with type, title, x_key, y_key, svg, meta; or None.
    """
    if not data or not isinstance(data, list):
        return None
    if len(data) < 2:
        logger.debug("Chart skipped: fewer than 2 rows")
        return None
    if not _check_chart_deps():
        logger.warning(
            "Chart dependencies not available in this process. "
            f"Install in the same Python that runs the API: pip install matplotlib seaborn "
            f"(Python: {sys.executable}). Then restart the API server."
        )
        return None

    truncated = len(data) > MAX_CHART_ROWS
    chart_data = data[:MAX_CHART_ROWS]
    rows_used = len(chart_data)
    cat_key, num_key, date_key = _classify_columns(chart_data)
    chart_type = _infer_chart_type(question)
    logger.info(f"Chart type: {chart_type}")
    title = (question[:80] + ("..." if len(question) > 80 else "")).strip() or "Chart"

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    palette = chart_colors.get_palette
    primary_color = chart_colors.get_primary_color()

    meta = {"rows_used": rows_used, "truncated": truncated}

    try:
        # Line: need at least one numeric series. X = date_key, cat_key, or index.
        if chart_type == "line" and num_key:
            if date_key:
                xs = [str(row.get(date_key, "")) for row in chart_data]
            elif cat_key:
                xs = [str(row.get(cat_key, "")) or "Unknown" for row in chart_data]
            else:
                xs = [str(i) for i in range(len(chart_data))]
            ys = [_safe_float(row.get(num_key)) for row in chart_data]
            x_vals = list(range(len(xs)))
            # Smooth curve via cubic spline (numpy only; matplotlib brings numpy)
            try:
                import numpy as np
                n = len(ys)
                if n >= 4:
                    # Natural cubic spline: evaluate at dense points for smooth line
                    x_smooth = np.linspace(0, n - 1, max((n - 1) * 10, 50))
                    y_smooth = _cubic_spline_smooth(np.arange(n), np.array(ys, dtype=float), x_smooth)
                    ax.plot(x_smooth, y_smooth, linewidth=2, color=primary_color)
                else:
                    ax.plot(x_vals, ys, linewidth=2, color=primary_color)
                ax.scatter(x_vals, ys, s=25, color=primary_color, zorder=5)
            except ImportError:
                ax.plot(x_vals, ys, marker="o", markersize=5, linewidth=2, color=primary_color)
            ax.set_xticks(x_vals)
            ax.set_xticklabels(xs, rotation=45, ha="right")
            ax.set_ylabel(num_key)
            ax.set_xlabel(date_key or cat_key or "x")
            x_key, y_key = date_key or cat_key or "x", num_key
        # Pie: categorical + numeric (aggregate by category).
        elif chart_type == "pie" and cat_key and num_key:
            agg: Dict[str, float] = {}
            for row in chart_data:
                lbl = str(row.get(cat_key, "")) or "Unknown"
                agg[lbl] = agg.get(lbl, 0) + _safe_float(row.get(num_key))
            labels = list(agg.keys())[:15]
            sizes = list(agg.values())[:15]
            colors = palette(len(labels))
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
            ax.axis("equal")
            x_key, y_key = cat_key, num_key
        # Bar: only when bar was requested or as fallback for plottable data.
        elif chart_type == "bar" and (cat_key or num_key):
            if cat_key and num_key:
                agg = {}
                for row in chart_data:
                    lbl = str(row.get(cat_key, "")) or "Unknown"
                    agg[lbl] = agg.get(lbl, 0) + _safe_float(row.get(num_key))
                labels = list(agg.keys())[:20]
                values = list(agg.values())[:20]
            elif num_key:
                labels = [str(i) for i in range(len(chart_data))]
                values = [_safe_float(row.get(num_key)) for row in chart_data]
            else:
                from collections import Counter
                counts = Counter(str(row.get(cat_key, "")) or "Unknown" for row in chart_data)
                items = counts.most_common(20)
                labels = [k for k, _ in items]
                values = [v for _, v in items]
            ax.bar(range(len(labels)), values, color=palette(len(labels)))
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")
            if num_key:
                ax.set_ylabel(num_key)
            ax.set_xlabel(cat_key or "Category")
            x_key, y_key = cat_key or "Category", num_key
        else:
            logger.debug("Chart skipped: no suitable columns for chart_type=%s", chart_type)
            plt.close(fig)
            return None

        ax.set_title(title)
        fig.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="svg", bbox_inches="tight")
        plt.close(fig)
        svg_str = buf.getvalue().decode("utf-8")
        if len(svg_str) > MAX_SVG_LENGTH:
            logger.warning(f"Chart SVG too large ({len(svg_str)} chars), skipping")
            return None

        return {
            "type": chart_type,
            "title": title,
            "x_key": x_key,
            "y_key": y_key,
            "svg": svg_str,
            "meta": meta,
        }
    except Exception as e:
        logger.warning(f"Chart generation failed: {e}")
        try:
            plt.close(fig)
        except Exception:
            pass
        return None
