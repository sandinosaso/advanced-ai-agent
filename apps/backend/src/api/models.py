"""
Pydantic models for API request and response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint
    
    Attributes:
        message: The user's question or message (1-2000 characters)
        conversation_id: Optional conversation ID for tracking multi-turn conversations
    """
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="The user's question or message to the AI agent"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for multi-turn conversations"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "How many technicians are active?",
                    "conversation_id": "conv-123"
                },
                {
                    "message": "What are the overtime rules?"
                }
            ]
        }
    }


class ChatToken(BaseModel):
    """
    Individual token in the SSE stream
    
    Token types:
    - reasoning: Intermediate reasoning/thinking (classification, SQL generation, etc.)
    - final_answer: The final response to show the user
    - tool_call: Tool execution marker (e.g., "Querying database...")
    - error: Error message
    
    Attributes:
        token: The text token being streamed
        type: Type of token (reasoning, final_answer, tool_call, error)
    """
    token: str = Field(..., description="The text token")
    type: Literal["reasoning", "final_answer", "tool_call", "error"] = Field(
        default="final_answer",
        description="Type of token being streamed"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "SELECT COUNT(*) FROM technicians",
                    "type": "reasoning"
                },
                {
                    "token": "There are 10 active technicians.",
                    "type": "final_answer"
                },
                {
                    "token": "[Using SQLQueryAgent]",
                    "type": "tool_call"
                }
            ]
        }
    }


class ChatComplete(BaseModel):
    """
    Stream completion marker
    
    Sent as the final event in an SSE stream to indicate completion
    
    Attributes:
        done: Always True, indicates stream is complete
        metadata: Optional metadata about the completed response including token counts
    """
    done: bool = Field(default=True, description="Stream completion flag")
    metadata: Optional[dict] = Field(
        None,
        description="Metadata with token counts: tokens_sent, reasoning_tokens, final_tokens"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "done": True,
                    "metadata": {
                        "tokens_sent": 28,
                        "reasoning_tokens": 22,
                        "final_tokens": 6
                    }
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
