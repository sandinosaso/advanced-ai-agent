"""
Chart color palettes aligned with frontend (base-web/packages/shared chartColors.jsx).

Single source of hex colors for matplotlib/seaborn. Change these to keep API charts
in sync with the frontend.
"""

from typing import List

# -----------------------------------------------------------------------------
# Base color (align with frontend: VITE_BASE_COLOR or "#3B82F6")
# -----------------------------------------------------------------------------
BASE_COLOR = "#3B82F6"

# -----------------------------------------------------------------------------
# Cool palette - blues, teals, purples (from frontend COOL_PALETTE rgba)
# -----------------------------------------------------------------------------
COOL_PALETTE: List[str] = [
    "#3B82F6",  # Blue
    "#0EA5E9",  # Sky Blue
    "#06B6D4",  # Cyan
    "#14B8A6",  # Teal
    "#10B981",  # Emerald (cool green)
    "#6366F1",  # Indigo
    "#8B5CF6",  # Violet
    "#A855F7",  # Purple
    "#93C5FD",  # Light Blue
    "#67E8F9",  # Light Cyan
]

# -----------------------------------------------------------------------------
# Warm palette - reds, oranges, yellows (from frontend WARM_PALETTE)
# -----------------------------------------------------------------------------
WARM_PALETTE: List[str] = [
    "#EF4444",  # Red
    "#FB923C",  # Orange
    "#EAB308",  # Yellow
    "#22C55E",  # Green
    "#EC4899",  # Pink
    "#F97316",  # Dark Orange
    "#F59E0B",  # Amber
    "#84CC16",  # Lime
    "#DC2626",  # Dark Red
    "#DB2777",  # Hot Pink
]

# -----------------------------------------------------------------------------
# Vibrant palette - mix (from frontend VIBRANT_PALETTE)
# -----------------------------------------------------------------------------
VIBRANT_PALETTE: List[str] = [
    "#6366F1",  # Indigo
    "#EF4444",  # Red
    "#22C55E",  # Green
    "#FB923C",  # Orange
    "#A855F7",  # Purple
    "#EC4899",  # Pink
    "#0EA5E9",  # Sky
    "#EAB308",  # Yellow
    "#3B82F6",  # Blue
    "#10B981",  # Emerald
]

# -----------------------------------------------------------------------------
# Primary monochromatic (frontend: generateMonochromaticPalette(BASE_COLOR, 10))
# Light to dark. Approximate 10 steps from +40% lighter to -60% darker.
# -----------------------------------------------------------------------------
PRIMARY_PALETTE: List[str] = [
    "#6BA3F7",  # lighter
    "#5A98F7",
    "#4A8DF6",
    "#3B82F6",  # base
    "#3270E5",
    "#295ED4",
    "#204CC3",
    "#183AB2",
    "#1028A1",
    "#081690",  # darker
]

# Default palette for bar/pie (match frontend DEFAULT_PALETTE = PRIMARY_PALETTE)
DEFAULT_PALETTE: List[str] = PRIMARY_PALETTE

# Single colors for line chart, single series, etc. (frontend CHART_COLORS)
CHART_COLORS = {
    "primary": BASE_COLOR,
    "secondary": "#0EA5E9",   # Sky Blue
    "success": "#10B981",     # Emerald
    "info": "#06B6D4",       # Cyan
    "warning": "#EAB308",    # Yellow
    "danger": "#EF4444",    # Red
    "purple": "#A855F7",
    "teal": "#14B8A6",
}


def get_palette(count: int, palette: List[str] | None = None) -> List[str]:
    """Return `count` colors from the given palette (or DEFAULT_PALETTE). Repeats if needed."""
    p = palette or DEFAULT_PALETTE
    if count <= 0:
        return []
    if count <= len(p):
        return p[:count]
    return (p * ((count // len(p)) + 1))[:count]


def get_primary_color() -> str:
    """Single color for line chart / single series."""
    return CHART_COLORS["primary"]
