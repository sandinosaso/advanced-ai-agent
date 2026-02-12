"""
Chart node - optionally generate a chart (ChartSpec + SVG) when user asked to visualize data.

Runs only on the SQL path after we have sql_structured_result.
Uses two signals for intent: explicit chart keywords, or follow-up (e.g. "chart that", "make it a pie").
"""

from src.agents.orchestrator.state import AgentState
from src.agents.orchestrator.context import OrchestratorContext
from src.charts import generate_chart

# Explicit: user clearly asked for a chart/visualization
VISUALIZATION_KEYWORDS = (
    "chart",
    "graph",
    "visualize",
    "visualization",
    "plot",
    "pie",
    "bar chart",
    "bar graph",
    "line chart",
    "show me a chart",
)

# Follow-up: short references to charting the previous/current result
FOLLOWUP_CHART_PHRASES = (
    "chart that",
    "graph that",
    "plot that",
    "visualize that",
    "make it a pie",
    "make it a bar",
    "as a pie chart",
    "as a bar chart",
    "as a chart",
    "that as a chart",
    "group by week",  # common re-aggregation ask
)

# Words that together with "that"/"it" indicate chart follow-up
CHART_WORDS = ("chart", "graph", "plot", "visualize", "pie", "bar")


def _wants_visualization(state: AgentState) -> bool:
    """
    True if we should generate a chart.

    Two signals:
    1) Explicit: question contains chart/graph/visualize/plot/pie/bar etc.
    2) Follow-up: short question with "that"/"it" + a chart word, and we have data (this turn or in memory).
    """
    question = state.get("question") or ""
    if not question or not isinstance(question, str):
        return False
    q = question.lower().strip()

    if any(kw in q for kw in VISUALIZATION_KEYWORDS):
        return True
    if any(phrase in q for phrase in FOLLOWUP_CHART_PHRASES):
        return True

    # Contextual follow-up: short question + "that" or "it" + chart word
    if len(q) > 80:
        return False
    has_that_or_it = " that " in f" {q} " or " it " in f" {q} " or q.startswith("that ") or q.startswith("it ")
    has_chart_word = any(w in q for w in CHART_WORDS)
    has_data_this_turn = state.get("sql_structured_result") and len(state.get("sql_structured_result") or []) > 0
    has_prior_results = bool(state.get("query_result_memory"))

    if has_that_or_it and has_chart_word and (has_data_this_turn or has_prior_results):
        return True
    return False


def maybe_generate_chart_node(state: AgentState, ctx: OrchestratorContext) -> AgentState:
    """
    If the user asked for a chart (explicit or follow-up) and we have SQL structured result,
    generate ChartSpec (type, title, x_key, y_key, svg, meta) and set chart_spec.
    """
    state = dict(state)
    state["chart_spec"] = None

    data = state.get("sql_structured_result")
    if not data or not isinstance(data, list) or len(data) == 0:
        return state

    if not _wants_visualization(state):
        return state

    spec = generate_chart(data, state.get("question") or "")
    if spec:
        state["chart_spec"] = spec
    return state
