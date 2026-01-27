"""
Internal chat streaming endpoint using Server-Sent Events (SSE)

This is an internal service API called by the Node.js BFF layer.
It emits semantic events, not UI-specific tokens.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from loguru import logger

from src.api.models import ChatStreamRequest, StreamEvent
from src.agents.orchestrator_agent import OrchestratorAgent


router = APIRouter(prefix="/internal/chat", tags=["internal"])


async def stream_orchestrator_response(
    message: str,
    conversation_id: str,
    user_id: str,
    company_id: str
) -> AsyncGenerator[str, None]:
    """
    Stream semantic events from OrchestratorAgent
    
    Emits structured events for Node.js to map to UI concepts.
    Does not contain UI-specific logic (emojis, labels, etc.)
    
    Args:
        message: User's question
        conversation_id: Conversation ID from Node.js
        user_id: Authenticated user ID
        company_id: Tenant ID for data isolation
    
    Yields:
        SSE-formatted strings with semantic events
    """
    try:
        logger.info(f"Stream started - conversation={conversation_id}, user={user_id}, company={company_id}")
        logger.debug(f"Message: {message[:100]}...")
        
        # Initialize agent
        agent = OrchestratorAgent()
        
        # Prepare initial state
        # TODO: Load conversation history from database using conversation_id
        initial_state = {
            "messages": [],
            "question": message,
            "next_step": "classify",
            "sql_result": None,
            "sql_structured_result": None,
            "rag_result": None,
            "final_answer": None,
            "final_structured_data": None
        }
        
        # Track statistics
        total_tokens = 0
        current_node = None
        final_structured_data = None  # Track structured data for final answer
        first_final_token = True  # Track if this is the first token in final channel
        
        # Stream events from the agent workflow
        async for event in agent.astream_events(initial_state, version="v1"):
            event_type = event.get("event")
            event_name = event.get("name", "")
            
            # Track current node
            if event_type in ["on_chain_start", "on_llm_start"]:
                # Detect node transitions
                if event_name == "classify":
                    current_node = "classify"
                elif event_name == "sql_agent":
                    current_node = "sql_agent"
                    # Emit tool start event
                    tool_event = StreamEvent(
                        event="tool_start",
                        tool="sql_agent"
                    )
                    yield f"data: {tool_event.model_dump_json()}\n\n"
                elif event_name == "rag_agent":
                    current_node = "rag_agent"
                    # Emit tool start event
                    tool_event = StreamEvent(
                        event="tool_start",
                        tool="rag_agent"
                    )
                    yield f"data: {tool_event.model_dump_json()}\n\n"
                elif event_name == "finalize":
                    current_node = "final"
                    first_final_token = True  # Reset for new finalize step
            
            # Capture structured data from orchestrator's sql_agent node completion
            # The sql_agent node stores structured_result in sql_structured_result
            if event_type == "on_chain_end" and event_name == "sql_agent":
                event_data = event.get("data") or {}
                outputs = event_data.get("output", {}) if isinstance(event_data, dict) else {}
                # The orchestrator's sql_agent node stores structured data here
                sql_structured = outputs.get("sql_structured_result") if isinstance(outputs, dict) else None
                if sql_structured:
                    final_structured_data = sql_structured
                    logger.info(f"✅ Captured structured_data from sql_agent node: {len(final_structured_data)} items")
                else:
                    logger.debug(f"sql_agent node output keys: {list(outputs.keys()) if isinstance(outputs, dict) else 'not a dict'}")
                    logger.debug(f"sql_structured_result not found in output")
            
            # Also capture from finalize step output (backup - should have final_structured_data)
            if event_type == "on_chain_end" and event_name == "finalize":
                event_data = event.get("data") or {}
                outputs = event_data.get("output", {}) if isinstance(event_data, dict) else {}
                # Finalize step should have final_structured_data (copied from sql_structured_result)
                final_structured_from_finalize = outputs.get("final_structured_data") if isinstance(outputs, dict) else None
                if final_structured_from_finalize:
                    if final_structured_data is None:
                        final_structured_data = final_structured_from_finalize
                        logger.info(f"✅ Captured structured_data from finalize step: {len(final_structured_data)} items")
                    else:
                        logger.debug(f"Already had structured_data from sql_agent, finalize also has {len(final_structured_from_finalize)} items")
                else:
                    logger.debug(f"finalize node output keys: {list(outputs.keys()) if isinstance(outputs, dict) else 'not a dict'}")
                    logger.debug(f"final_structured_data not found in finalize output")
            
            # Stream content tokens
            if event_type == "on_chat_model_stream":
                event_data = event.get("data")
                if not event_data or not isinstance(event_data, dict):
                    continue
                chunk = event_data.get("chunk")
                if not chunk:
                    continue
                
                if hasattr(chunk, "content") and chunk.content:
                    # Skip classification tokens (internal routing only)
                    if current_node == "classify":
                        continue
                    
                    total_tokens += 1
                    
                    # Include structured_data in the first token of final channel
                    # This allows BFF to convert arrays to markdown before/while streaming content
                    structured_data_for_token = None
                    if current_node == "final" and first_final_token:
                        if final_structured_data is not None:
                            # Include structured_data in the first token only
                            structured_data_for_token = final_structured_data
                            first_final_token = False  # Mark that we've sent it
                            logger.info(f"✅ Including structured_data in first final token: {len(structured_data_for_token)} items")
                        else:
                            logger.debug(f"⚠️ First final token but no structured_data available (final_structured_data is None)")
                            first_final_token = False  # Still mark as sent to avoid repeated warnings
                    
                    # Emit semantic token event
                    token_event = StreamEvent(
                        event="token",
                        channel=current_node,
                        content=chunk.content,
                        structured_data=structured_data_for_token
                    )
                    yield f"data: {token_event.model_dump_json()}\n\n"
            
            # Detect route decisions from classification result
            elif event_type == "on_chain_end" and event_name == "classify":
                # Extract classification result
                event_data = event.get("data") or {}
                outputs = event_data.get("output", {}) if isinstance(event_data, dict) else {}
                next_step = outputs.get("next_step", "") if isinstance(outputs, dict) else ""
                
                if next_step in ["sql", "rag"]:
                    route_event = StreamEvent(
                        event="route_decision",
                        route=next_step
                    )
                    yield f"data: {route_event.model_dump_json()}\n\n"
        
        logger.info(f"Stream completed - tokens={total_tokens}")
        
        # Send completion event
        complete_event = StreamEvent(
            event="complete",
            stats={
                "tokens": total_tokens,
                "conversation_id": conversation_id
            }
        )
        yield f"data: {complete_event.model_dump_json()}\n\n"
        
    except Exception as e:
        error_message = str(e) if e else "Unknown error"
        # Log error - use logger.exception to capture full traceback
        # Avoid f-strings with error messages that might contain curly braces
        logger.exception("Stream error occurred")
        # Send error event
        try:
            error_event = StreamEvent(
                event="error",
                error=error_message
            )
            yield f"data: {error_event.model_dump_json()}\n\n"
        except Exception as inner_e:
            # Fallback if StreamEvent creation fails
            logger.exception("Failed to create error event")
            # Escape curly braces in error message for JSON string formatting
            escaped_message = error_message.replace("{", "{{").replace("}", "}}")
            yield f'data: {{"type":"error","message":"❌ Error: {escaped_message}","metadata":{{}}}}\n\n'


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest):
    """
    Internal streaming endpoint for agent execution
    
    **Called by:** Node.js BFF layer (not browsers directly)
    
    **Purpose:** Execute OrchestratorAgent and stream semantic events
    
    **Authentication:** Trusts Node.js - does not authenticate
    
    **Request:**
    ```json
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
    ```
    
    **Response:** SSE stream with semantic events
    
    **Event Types:**
    
    1. **route_decision** - Agent routing decision
    ```json
    {"event": "route_decision", "route": "sql"}
    ```
    
    2. **tool_start** - Tool execution beginning
    ```json
    {"event": "tool_start", "tool": "sql_agent"}
    ```
    
    3. **token** - Content token with channel
    ```json
    {"event": "token", "channel": "final", "content": "There are"}
    ```
    
    4. **complete** - Stream finished
    ```json
    {"event": "complete", "stats": {"tokens": 42}}
    ```
    
    5. **error** - Error occurred
    ```json
    {"event": "error", "error": "message"}
    ```
    
    **Channels:**
    - `classify`: Classification reasoning (usually skipped)
    - `sql_agent`: SQL generation reasoning
    - `rag_agent`: RAG retrieval reasoning
    - `final`: Final answer to user
    
    **Node.js Integration:**
    
    Node.js BFF layer maps semantic events to UI concepts:
    ```javascript
    if (event.event === "tool_start") {
      if (event.tool === "sql_agent") {
        ui.emit("🔍 Querying database");
      } else if (event.tool === "rag_agent") {
        ui.emit("📚 Searching knowledge base");
      }
    }
    
    if (event.channel === "final") {
      ui.appendToFinalAnswer(event.content);
    }
    ```
    
    Args:
        request: ChatStreamRequest with input and conversation context
    
    Returns:
        StreamingResponse with text/event-stream
    """
    logger.info(
        f"Internal stream request - "
        f"conversation={request.conversation.id}, "
        f"user={request.conversation.user_id}, "
        f"company={request.conversation.company_id}"
    )
    
    return StreamingResponse(
        stream_orchestrator_response(
            message=request.input.message,
            conversation_id=request.conversation.id,
            user_id=request.conversation.user_id,
            company_id=request.conversation.company_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
