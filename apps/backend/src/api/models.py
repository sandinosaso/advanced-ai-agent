"""
Pydantic models for internal API contract

This is an internal service API - UI concepts are handled by the Node.js BFF layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List


class AgentInput(BaseModel):
    """User's message input to the agent"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question or message"
    )


class ConversationContext(BaseModel):
    """
    Conversation context provided by the Node.js BFF
    
    This includes authentication and tenant information that Python trusts.
    """
    id: str = Field(..., description="Conversation/session ID")
    user_id: str = Field(..., description="Authenticated user ID")
    company_id: str = Field(..., description="Tenant/company ID for data isolation")


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
    channel: Optional[Literal["classify", "sql_agent", "rag_agent", "final"]] = None
    content: Optional[str] = None  # Raw content (backward compatible)
    structured_data: Optional[List[Dict[str, Any]]] = None  # Structured array for BFF markdown conversion
    tool: Optional[str] = None
    route: Optional[Literal["sql", "rag"]] = None
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
