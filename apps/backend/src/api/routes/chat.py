"""
Chat streaming endpoint using Server-Sent Events (SSE)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from loguru import logger

from src.api.models import ChatRequest, ChatToken, ChatComplete
from src.agents.orchestrator_agent import OrchestratorAgent


router = APIRouter(prefix="/api/chat", tags=["chat"])


async def stream_orchestrator_response(
    message: str, 
    conversation_id: str | None
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from OrchestratorAgent using LangChain events
    
    This generator:
    1. Initializes the OrchestratorAgent
    2. Streams events from the LangGraph workflow
    3. Filters for chat model token events
    4. Yields SSE-formatted messages
    
    Args:
        message: User's question/message
        conversation_id: Optional conversation ID for tracking
    
    Yields:
        SSE-formatted strings: "data: {json}\n\n"
    """
    try:
        logger.info(f"Starting stream for message: {message[:50]}...")
        
        # Initialize agent
        agent = OrchestratorAgent()
        
        # Prepare initial state
        initial_state = {
            "messages": [],
            "question": message,
            "next_step": "classify",
            "sql_result": None,
            "rag_result": None,
            "final_answer": None
        }
        
        # Track if we've sent any tokens
        tokens_sent = 0
        reasoning_tokens = 0
        final_tokens = 0
        current_node = None
        route_detected = False
        classification_buffer = ""
        
        # Stream events from the workflow
        async for event in agent.workflow.astream_events(
            initial_state,
            version="v1"
        ):
            event_type = event.get("event")
            event_name = event.get("name", "")
            event_tags = event.get("tags", [])
            
            # Track which node we're currently in by looking at multiple event types
            if event_type in ["on_chain_start", "on_llm_start"]:
                # Log all tags for debugging (first 3 events only)
                if tokens_sent < 3:
                    logger.info(f"Event: {event_type}, Name: {event_name}, Tags: {event_tags}")
                
                # Check the NAME field for node information (not tags!)
                if event_name == "classify":
                    current_node = "classify"
                    logger.debug("Entering classify node")
                elif event_name == "sql_agent":
                    current_node = "sql_agent"
                    # Emit route decision as tool_call
                    if not route_detected:
                        route_event = ChatToken(
                            token="🔍 Querying database",
                            type="tool_call"
                        )
                        yield f"data: {route_event.model_dump_json()}\n\n"
                        route_detected = True
                    logger.debug("Routing to SQL agent")
                elif event_name == "rag_agent":
                    current_node = "rag_agent"
                    # Emit route decision as tool_call
                    if not route_detected:
                        route_event = ChatToken(
                            token="📚 Searching knowledge base",
                            type="tool_call"
                        )
                        yield f"data: {route_event.model_dump_json()}\n\n"
                        route_detected = True
                    logger.debug("Routing to RAG agent")
                elif event_name == "finalize":
                    current_node = "finalize"
                    logger.debug("Detected finalize node")
                
                # Fallback: Also check tags for node information
                for tag in event_tags:
                    # Detect classify node
                    if "classify" in tag.lower() and ":" in tag:
                        current_node = "classify"
                        logger.debug("Entering classify node")
                        break
                    # Look for patterns like: graph:step:3, seq:step:finalize, etc.
                    elif "finalize" in tag.lower():
                        current_node = "finalize"
                        logger.debug(f"Detected finalize node from tag: {tag}")
                        break
                    elif "sql_agent" in tag.lower():
                        current_node = "sql_agent"
                        # Emit route decision as tool_call
                        if not route_detected:
                            route_event = ChatToken(
                                token="🔍 Querying database",
                                type="tool_call"
                            )
                            yield f"data: {route_event.model_dump_json()}\n\n"
                            route_detected = True
                        logger.debug(f"Routing to SQL agent")
                        break
                    elif "rag_agent" in tag.lower():
                        current_node = "rag_agent"
                        # Emit route decision as tool_call
                        if not route_detected:
                            route_event = ChatToken(
                                token="📚 Searching knowledge base",
                                type="tool_call"
                            )
                            yield f"data: {route_event.model_dump_json()}\n\n"
                            route_detected = True
                        logger.debug(f"Routing to RAG agent")
                        break
                    elif tag.startswith("graph:step:"):
                        pass
                    elif ":" in tag and tag.split(":")[-1] in ["classify", "sql_agent", "rag_agent", "finalize"]:
                        node_name = tag.split(":")[-1]
                        current_node = node_name
                        
                        # Emit route decision when entering agent nodes
                        if node_name == "sql_agent" and not route_detected:
                            route_event = ChatToken(
                                token="🔍 Querying database",
                                type="tool_call"
                            )
                            yield f"data: {route_event.model_dump_json()}\n\n"
                            route_detected = True
                        elif node_name == "rag_agent" and not route_detected:
                            route_event = ChatToken(
                                token="📚 Searching knowledge base",
                                type="tool_call"
                            )
                            yield f"data: {route_event.model_dump_json()}\n\n"
                            route_detected = True
                        
                        logger.debug(f"Entering node: {current_node}")
                        break
                
                # Also check event name
                if "finalize" in event_name.lower():
                    current_node = "finalize"
                    logger.debug(f"Detected finalize node from name: {event_name}")
            
            # Filter for chat model streaming events
            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                
                # Extract content from the chunk
                if hasattr(chunk, "content") and chunk.content:
                    
                    # SKIP ALL TOKENS FROM CLASSIFY NODE
                    # The classify node only returns "SQL" or "RAG" for routing
                    # We'll show the route decision as a tool_call when entering sql_agent/rag_agent
                    if current_node == "classify":
                        continue  # Skip this token completely
                    
                    tokens_sent += 1
                    
                    # Log first token to help debug
                    if tokens_sent == 1:
                        logger.info(f"First token - current_node: {current_node}")
                    
                    # Determine if we're in the finalize node (final answer)
                    # or in other nodes (reasoning)
                    if current_node == "finalize":
                        token_type = "final_answer"
                        final_tokens += 1
                    else:
                        token_type = "reasoning"
                        reasoning_tokens += 1
                    
                    token_data = ChatToken(
                        token=chunk.content,
                        type=token_type
                    )
                    yield f"data: {token_data.model_dump_json()}\n\n"
            
            # Capture tool execution starts
            elif event["event"] == "on_tool_start":
                tool_name = event.get("name", "unknown")
                logger.debug(f"Tool started: {tool_name}")
                # Optionally send a marker that a tool is being used
                # This is useful for showing "Querying database..." in UI
                tool_marker = ChatToken(
                    token=f"[Using {tool_name}]",
                    type="tool_call"
                )
                yield f"data: {tool_marker.model_dump_json()}\n\n"
        
        logger.info(f"Stream completed. Tokens sent: {tokens_sent} (reasoning: {reasoning_tokens}, final: {final_tokens})")
        
        # Send completion marker
        complete = ChatComplete(
            done=True,
            metadata={
                "tokens_sent": tokens_sent,
                "reasoning_tokens": reasoning_tokens,
                "final_tokens": final_tokens
            }
        )
        yield f"data: {complete.model_dump_json()}\n\n"
        
    except Exception as e:
        logger.error(f"Error in stream: {str(e)}", exc_info=True)
        # Send error token
        error_data = ChatToken(
            token=f"Error: {str(e)}",
            type="error"
        )
        yield f"data: {error_data.model_dump_json()}\n\n"
        
        # Still send completion
        complete = ChatComplete(done=True, metadata={"error": True})
        yield f"data: {complete.model_dump_json()}\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses using Server-Sent Events (SSE)
    
    This endpoint:
    - Accepts a chat message
    - Routes it through the OrchestratorAgent
    - Streams tokens back in real-time using SSE
    - Tags tokens by type: reasoning vs final_answer
    
    **Example Usage:**
    
    ```bash
    curl -N -X POST http://localhost:8000/api/chat/stream \\
         -H "Content-Type: application/json" \\
         -d '{"message": "How many technicians are active?"}'
    ```
    
    **Response Format:**
    
    Each line is an SSE event. The stream includes:
    
    1. **Reasoning tokens** (classification, SQL generation):
    ```
    data: {"token": "SQL", "type": "reasoning"}
    data: {"token": "SELECT COUNT(*)", "type": "reasoning"}
    ```
    
    2. **Tool execution markers**:
    ```
    data: {"token": "[Using SQLQueryAgent]", "type": "tool_call"}
    ```
    
    3. **Final answer tokens**:
    ```
    data: {"token": "There", "type": "final_answer"}
    data: {"token": " are", "type": "final_answer"}
    data: {"token": " 10", "type": "final_answer"}
    ```
    
    4. **Completion marker with metadata**:
    ```
    data: {"done": true, "metadata": {"tokens_sent": 28, "reasoning_tokens": 22, "final_tokens": 6}}
    ```
    
    **Token Types:**
    - `reasoning`: Intermediate AI thinking (show in gray bubble)
    - `final_answer`: Final response to user (main chat bubble)
    - `tool_call`: Tool execution indicator
    - `error`: Error messages
    
    **Frontend Usage:**
    
    Use different UI for reasoning vs final answer:
    ```typescript
    if (type === 'reasoning') {
      // Show in "thinking..." bubble (gray, replaceable)
      updateThinkingBubble(token);
    } else if (type === 'final_answer') {
      // Hide thinking, show final answer
      showFinalAnswer(token);
    }
    ```
    
    Args:
        request: ChatRequest with message and optional conversation_id
    
    Returns:
        StreamingResponse with text/event-stream content type
    """
    logger.info(f"Received chat stream request: {request.message[:100]}...")
    
    return StreamingResponse(
        stream_orchestrator_response(
            request.message, 
            request.conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
