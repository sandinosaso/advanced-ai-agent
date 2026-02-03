"""
Conversation context models for internal API contract

This is an internal service API - UI concepts are handled by the Node.js BFF layer.
"""

from pydantic import BaseModel, Field


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
