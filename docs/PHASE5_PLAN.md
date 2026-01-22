# Phase 5: API Exposure & Real-Time Streaming - Detailed Plan

## 🎯 Learning Objectives

By the end of Phase 5, you will understand:

- **API Architecture**: Designing REST APIs for AI agents with streaming responses
- **Server-Sent Events (SSE)**: Real-time streaming from backend to frontend
- **FastAPI**: Building production-grade Python APIs
- **End-to-End Streaming**: Token-level streaming from LangChain → FastAPI → Node.js → Browser
- **Separation of Concerns**: ML services vs. business logic vs. frontend
- **Production Patterns**: CORS, error handling, request validation, timeouts

---

## 📚 Phase 5 Overview

**Goal**: Transform the command-line interactive OrchestratorAgent from Phase 4 into a web-accessible API that streams responses in real-time.

**Why It Matters**: 
- Users need a chat interface, not a terminal
- Streaming provides immediate feedback (like ChatGPT)
- Separating AI backend from frontend enables scalability
- Clean API boundaries allow frontend/backend teams to work independently

**Current State**: 
- ✅ Working OrchestratorAgent with SQL + RAG capabilities
- ✅ Interactive mode via `demo_orchestrator.py`
- ❌ No way to call this from a web application

**Target State**:
- ✅ FastAPI service exposing `/chat/stream` endpoint
- ✅ Real-time token streaming using SSE
- ✅ JSON request/response format
- ✅ Ready for Node.js proxy integration
- ✅ Frontend-ready architecture

---

## 🏗️ Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                          │
│                  (Future - Not in Phase 5)                      │
│                     EventSource API                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ SSE Stream
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Node.js Express API                          │
│                  (Future - Not in Phase 5)                      │
│                   Streaming Proxy Layer                         │
│            (Auth, Rate Limiting, Business Logic)                │
└────────────────────────────┬────────────────────────────────────┘
                             │ SSE Stream
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                      │
│                      ⭐ PHASE 5 FOCUS ⭐                         │
│                                                                 │
│  POST /api/chat/stream                                          │
│       ↓                                                         │
│  Request Validation (Pydantic)                                  │
│       ↓                                                         │
│  OrchestratorAgent.ainvoke()                                    │
│       ↓                                                         │
│  Stream LangChain Events                                        │
│       ↓                                                         │
│  SSE Response: data: {"token": "..."}\n\n                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 5 Scope

**In Scope**:
1. ✅ FastAPI application setup
2. ✅ Chat endpoint with SSE streaming
3. ✅ LangChain streaming callback integration
4. ✅ Request/response models (Pydantic)
5. ✅ Error handling and logging
6. ✅ CORS configuration for future frontend
7. ✅ Testing with curl/Postman

**Out of Scope** (Future phases):
- ❌ Node.js proxy layer
- ❌ React frontend
- ❌ Authentication/Authorization
- ❌ Rate limiting
- ❌ Database session management
- ❌ Deployment configuration

---

## 🛠️ Technology Stack

### Why FastAPI?

| Criteria | FastAPI | Flask | Django |
|----------|---------|-------|--------|
| **Async Support** | ✅ Native | ⚠️ Via extensions | ⚠️ Limited |
| **Type Safety** | ✅ Pydantic models | ❌ Manual | ⚠️ Optional |
| **Auto Docs** | ✅ OpenAPI/Swagger | ❌ Manual | ⚠️ DRF only |
| **Streaming** | ✅ StreamingResponse | ✅ generators | ⚠️ Complex |
| **Performance** | ✅ High (Starlette) | ⚠️ Moderate | ⚠️ Moderate |
| **Learning Curve** | ✅ Low | ✅ Low | ❌ High |

**Decision**: FastAPI for async streaming, auto-validation, and modern Python patterns.

### Why Server-Sent Events (SSE)?

| Technology | Use Case | Complexity | Browser Support |
|------------|----------|------------|-----------------|
| **SSE** | Server → Client streaming | ✅ Simple | ✅ Universal |
| **WebSockets** | Bi-directional real-time | ❌ Complex | ✅ Universal |
| **Long Polling** | Legacy compatibility | ⚠️ Inefficient | ✅ Universal |
| **HTTP/2 Push** | Resource hints | ❌ Deprecated | ❌ Limited |

**Decision**: SSE is perfect for one-way streaming (server → client), simple to implement, and works natively with LangChain streaming.

---

## 📋 Implementation Steps

### Step 1: FastAPI Project Setup

**File**: `apps/backend/src/api/__init__.py`

**Tasks**:
- Install FastAPI, Uvicorn, Pydantic
- Create API module structure
- Configure CORS for local development

**Dependencies** (add to `requirements.txt`):
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
python-multipart==0.0.6
```

---

### Step 2: Request/Response Models

**File**: `apps/backend/src/api/models.py`

**Models**:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "How many technicians are active?",
                    "conversation_id": "conv-123"
                }
            ]
        }
    }

class ChatToken(BaseModel):
    """Individual token in the stream"""
    token: str
    type: str = "content"  # content, thought, tool_call, error

class ChatComplete(BaseModel):
    """Stream completion marker"""
    done: bool = True
    metadata: Optional[dict] = None
```

**Why Pydantic?**
- Auto-validation (min_length prevents empty messages)
- Auto-documentation (shows up in Swagger UI)
- Type safety (catches bugs before runtime)

---

### Step 3: Streaming Endpoint

**File**: `apps/backend/src/api/routes/chat.py`

**Core Logic**:

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import AsyncGenerator

from src.agents.orchestrator_agent import OrchestratorAgent
from src.api.models import ChatRequest, ChatToken, ChatComplete

router = APIRouter(prefix="/api/chat", tags=["chat"])

async def stream_orchestrator_response(
    message: str, 
    conversation_id: Optional[str]
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from OrchestratorAgent using LangChain callbacks
    
    Yields SSE-formatted events:
        data: {"token": "Hello", "type": "content"}\n\n
    """
    try:
        # Initialize agent
        agent = OrchestratorAgent()
        
        # LangChain streaming callback
        async for event in agent.astream_events(
            {"question": message},
            version="v1"
        ):
            # Filter for token events
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    token_data = ChatToken(
                        token=chunk.content,
                        type="content"
                    )
                    yield f"data: {token_data.model_dump_json()}\n\n"
        
        # Send completion marker
        complete = ChatComplete(done=True)
        yield f"data: {complete.model_dump_json()}\n\n"
        
    except Exception as e:
        error_data = ChatToken(token=str(e), type="error")
        yield f"data: {error_data.model_dump_json()}\n\n"

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses using Server-Sent Events (SSE)
    
    Example usage:
        curl -N -X POST http://localhost:8000/api/chat/stream \
             -H "Content-Type: application/json" \
             -d '{"message": "How many technicians?"}'
    """
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
```

**Key Concepts**:
- `astream_events()`: LangChain's async streaming API
- `AsyncGenerator`: Python's async generator for yielding tokens
- SSE Format: `data: {...}\n\n` (two newlines required)
- Headers: Prevent buffering at reverse proxy level

---

### Step 4: Main FastAPI Application

**File**: `apps/backend/src/api/app.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.routes import chat
from src.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 FastAPI application starting...")
    yield
    logger.info("🛑 FastAPI application shutting down...")

app = FastAPI(
    title="Field Service Intelligence Agent API",
    description="Streaming chat API for AI-powered field service assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "fsia-api",
        "version": "1.0.0"
    }
```

---

### Step 5: Run Script

**File**: `apps/backend/run_api.py`

```python
"""
Development server for FastAPI application
Run: python run_api.py
"""
import uvicorn
from src.utils.logger import logger

if __name__ == "__main__":
    logger.info("Starting FastAPI development server...")
    
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info",
        access_log=True
    )
```

---

### Step 6: Update OrchestratorAgent for Streaming

**File**: `apps/backend/src/agents/orchestrator_agent.py`

**Required Change**: Ensure the graph supports streaming

```python
# Existing compile call - ensure streaming is enabled
self.graph = workflow.compile()

# Add streaming method
async def astream_events(self, input_data: dict, version: str = "v1"):
    """
    Stream events from LangChain execution
    
    This wraps the graph's astream_events method for FastAPI
    """
    async for event in self.graph.astream_events(input_data, version=version):
        yield event
```

**Note**: LangGraph already supports `astream_events()` natively - we just need to expose it.

---

## 🧪 Testing Strategy

### Level 1: Manual Testing with curl

**Test 1: Health Check**
```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "healthy", "service": "fsia-api", "version": "1.0.0"}
```

**Test 2: Streaming Chat**
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "How many technicians are active?"}'
```

Expected (streaming output):
```
data: {"token": "There", "type": "content"}

data: {"token": " are", "type": "content"}

data: {"token": " 10", "type": "content"}

data: {"token": " active", "type": "content"}

data: {"token": " technicians", "type": "content"}

data: {"done": true, "metadata": null}
```

### Level 2: Testing with Postman

1. Create new POST request to `http://localhost:8000/api/chat/stream`
2. Set header: `Content-Type: application/json`
3. Body (raw JSON):
   ```json
   {
     "message": "What are the overtime rules?"
   }
   ```
4. Send and observe streaming response

### Level 3: Python Test Client

**File**: `apps/backend/tests/test_api_streaming.py`

```python
import httpx
import asyncio

async def test_streaming():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/chat/stream",
            json={"message": "How many technicians?"},
            timeout=30.0
        ) as response:
            print("Streaming response:")
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    print(line)

if __name__ == "__main__":
    asyncio.run(test_streaming())
```

---

## 📊 Success Criteria

### Functional Requirements
- ✅ `/health` endpoint returns 200 OK
- ✅ `/api/chat/stream` accepts POST with JSON body
- ✅ Validates message length (1-2000 chars)
- ✅ Streams SSE events in correct format
- ✅ Returns completion marker when done
- ✅ Handles errors gracefully

### Non-Functional Requirements
- ✅ First token latency < 2 seconds
- ✅ No buffering (tokens stream immediately)
- ✅ CORS headers allow localhost:3000
- ✅ Auto-generated API docs at `/docs`
- ✅ Logging captures all requests

---

## 🚧 Common Pitfalls & Solutions

### Pitfall 1: Response Buffering

**Problem**: Tokens don't stream; entire response arrives at once

**Cause**: Uvicorn or nginx buffering

**Solution**:
```python
# In StreamingResponse headers
"X-Accel-Buffering": "no",  # Nginx
"Cache-Control": "no-cache"
```

### Pitfall 2: CORS Errors

**Problem**: Browser blocks requests from localhost:3000

**Cause**: Missing CORS middleware

**Solution**: Already included in `app.py` - verify `allow_origins`

### Pitfall 3: Slow First Token

**Problem**: 5+ second delay before streaming starts

**Cause**: Agent initialization happens per request

**Solution** (Phase 6):
```python
# Use dependency injection with singleton
from functools import lru_cache

@lru_cache()
def get_orchestrator():
    return OrchestratorAgent()
```

### Pitfall 4: Connection Timeouts

**Problem**: Stream cuts off after 30 seconds

**Cause**: Default HTTP timeout

**Solution**:
```python
# In uvicorn run
uvicorn.run(..., timeout_keep_alive=120)
```

---

## 📁 Updated Project Structure

```
apps/backend/
├── run_api.py                  # ⭐ NEW - FastAPI dev server
├── requirements.txt            # Updated with FastAPI deps
├── src/
│   ├── api/                    # ⭐ NEW - API module
│   │   ├── __init__.py
│   │   ├── app.py              # Main FastAPI app
│   │   ├── models.py           # Pydantic request/response models
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── chat.py         # Streaming chat endpoint
│   ├── agents/
│   │   ├── orchestrator_agent.py  # Updated with astream_events
│   │   ├── rag_agent.py
│   │   └── sql_agent.py
│   └── ...
└── tests/
    └── test_api_streaming.py   # ⭐ NEW - API tests
```

---

## 🎓 Learning Path

### Phase 5A: FastAPI Basics (2 hours)
1. Read [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
2. Implement `/health` endpoint
3. Add Pydantic request model
4. Test with Swagger UI at `/docs`

### Phase 5B: SSE Streaming (2 hours)
1. Read [StreamingResponse docs](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
2. Create simple streaming endpoint (hardcoded tokens)
3. Test with curl `-N` flag
4. Understand SSE format: `data: {...}\n\n`

### Phase 5C: LangChain Integration (3 hours)
1. Review [LangChain streaming docs](https://python.langchain.com/docs/expression_language/streaming)
2. Use `astream_events()` to capture tokens
3. Filter events for `on_chat_model_stream`
4. Yield formatted SSE messages

### Phase 5D: Production Readiness (2 hours)
1. Add error handling (try/except in stream)
2. Configure CORS properly
3. Add request logging
4. Write integration tests

**Total Time**: ~9 hours

---

## 🔄 Future Phases Preview

### Phase 6: Node.js Proxy Layer
- Express.js API gateway
- Authentication middleware
- Rate limiting
- Request forwarding to FastAPI
- Session management

### Phase 7: React Frontend
- Chat UI component
- EventSource API for SSE
- Message history
- Typing indicators
- Error states

### Phase 8: Production Deployment
- Docker containers
- Environment configs
- Monitoring & logging
- Load balancing
- CI/CD pipeline

---

## 📝 Summary

**What You're Building**: A production-ready FastAPI service that exposes your OrchestratorAgent via streaming REST API.

**Key Takeaways**:
1. **FastAPI** = Modern Python web framework with async/await
2. **SSE** = Simple, efficient one-way streaming (perfect for AI)
3. **StreamingResponse** = FastAPI's built-in streaming support
4. **astream_events()** = LangChain's streaming API
5. **Pydantic** = Type-safe request/response validation

**Next Steps**:
1. Install dependencies: `pip install fastapi uvicorn`
2. Create `src/api/` module structure
3. Implement models → routes → app
4. Test with curl
5. Verify in Swagger UI (`/docs`)

**You're Ready When**:
- You can curl the API and see tokens streaming
- First token arrives in < 2 seconds
- Errors are handled gracefully
- API docs are auto-generated

---

## 🎯 Phase 5 Checklist

### Setup
- [ ] Install FastAPI, Uvicorn, Pydantic
- [ ] Create `src/api/` module structure
- [ ] Add Pydantic models (`models.py`)

### Implementation
- [ ] Health check endpoint (`/health`)
- [ ] Chat streaming endpoint (`/api/chat/stream`)
- [ ] CORS middleware configuration
- [ ] Error handling in stream generator
- [ ] Update OrchestratorAgent for streaming

### Testing
- [ ] curl health check works
- [ ] curl streaming shows tokens incrementally
- [ ] Postman streaming test works
- [ ] Python httpx client test works
- [ ] Swagger UI at `/docs` is accessible

### Documentation
- [ ] API documented in Swagger
- [ ] README updated with run instructions
- [ ] Example curl commands tested
- [ ] Phase 5 completion doc created

---

**Let's build it! 🚀**
