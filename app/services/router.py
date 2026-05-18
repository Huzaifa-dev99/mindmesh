import json
import re
from typing import Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.core.logging import get_logger, log_timing, trace
from app.services.prompts import ROUTER_PROMPT_NAME, render_prompt

RouteName = Literal["retrieval", "web_search", "direct"]

logger = get_logger(__name__)


class RouteDecision(BaseModel):
    route: RouteName = Field(
        description="The selected route: retrieval, web_search, or direct."
    )
    reasoning: str = Field(default="", description="Brief reason for the route.")


def _coerce_decision(value) -> RouteDecision:
    if isinstance(value, RouteDecision):
        return value
    if isinstance(value, dict):
        return RouteDecision.model_validate(value)

    content = str(getattr(value, "content", value) or "").strip()
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if match:
        return RouteDecision.model_validate(json.loads(match.group(0)))

    raise ValueError("Router did not return valid JSON.")


def route_query(query: str, llm=None) -> RouteDecision:
    trace("Query routing started", logger)
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    prompt = render_prompt(ROUTER_PROMPT_NAME, query=query.strip())

    if llm is None:
        from app.core.clients import get_llm

        llm = get_llm()

    with log_timing(logger, "query_routing", query_length=len(query.strip())):
        try:
            structured_llm = llm.with_structured_output(RouteDecision)
            decision = _coerce_decision(
                structured_llm.invoke([HumanMessage(content=prompt)])
            )
        except Exception:
            logger.warning("structured query routing failed; using text fallback", exc_info=True)
            response = llm.invoke([HumanMessage(content=prompt)])
            decision = _coerce_decision(response)

    logger.info(
        "query routing completed",
        extra={"event": {"route": decision.route, "reasoning": decision.reasoning}},
    )
    trace(f"Query routing completed with route {decision.route}", logger)
    return decision
