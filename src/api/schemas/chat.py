"""
Chat streaming models for internal API contract

This is an internal service API - UI concepts are handled by the Node.js BFF layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List

from src.api.schemas.conversation import AgentInput, ConversationContext


class ChatStreamRequest(BaseModel):
    """
    Internal API request for chat streaming
    
    This is called by the Node.js BFF, not directly by browsers.
    """
    input: AgentInput
    conversation: ConversationContext
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "input": {
                        "message": "How many technicians are active?"
                    },
                    "conversation": {
                        "id": "conv-uuid-123",
                        "user_id": "user-456",
                        "company_id": "company-789"
                    }
                }
            ]
        }
    }


class StreamEvent(BaseModel):
    """
    Semantic event emitted during agent execution
    
    Event types:
    - token: Content token (channel indicates which node/phase)
    - tool_start: Tool execution beginning
    - route_decision: Agent routing decision
    - complete: Stream finished
    - error: Error occurred
    """
    event: Literal["token", "tool_start", "route_decision", "complete", "error"]
    
    # Optional fields depending on event type
    channel: Optional[Literal["classify", "sql_agent", "rag_agent", "general_agent", "final"]] = None
    content: Optional[str] = None  # Raw content (backward compatible)
    structured_data: Optional[List[Dict[str, Any]]] = None  # Structured array for BFF markdown conversion
    tool: Optional[str] = None
    route: Optional[Literal["sql", "rag", "general"]] = None
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event": "token",
                    "channel": "final",
                    "content": "There are 10 technicians"
                },
                {
                    "event": "tool_start",
                    "tool": "sql_agent"
                },
                {
                    "event": "route_decision",
                    "route": "sql"
                },
                {
                    "event": "complete",
                    "stats": {"tokens": 42, "duration_ms": 1500}
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """
    Health check response
    
    Attributes:
        status: Service health status
        service: Service name
        version: API version
    """
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
