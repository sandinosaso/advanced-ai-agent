# Internal API Refactoring - Phase 5 Completion

## Overview

The FastAPI service has been refactored from a frontend-aware API to a **clean internal service** that follows the Backend-for-Frontend (BFF) pattern.

## Architecture

```
Browser ←→ Node.js (BFF) ←→ Python (FastAPI)
          ↑ Public API      ↑ Internal API
          ↑ Auth, UX       ↑ Agent Logic
```

### Separation of Concerns

| Layer | Responsibility |
|-------|---------------|
| **Browser** | UI rendering, user interaction |
| **Node.js BFF** | Authentication, cookies, session management, UX mapping, emojis, public API contract |
| **Python FastAPI** | Agent orchestration, LangGraph workflow, semantic events, memory persistence, database access |

## What Changed

### 1. Endpoint Renamed ✅

**Before:**
```
POST /api/chat/stream
```

**After:**
```
POST /internal/chat/stream
```

**Why:** Signals this is an internal-only service, not publicly exposed.

---

### 2. Request Model - Richer Context ✅

**Before (frontend-shaped):**
```json
{
  "message": "How many technicians are active?",
  "conversation_id": "conv-123"
}
```

**After (internal contract):**
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

**Why:**
- Explicit tenant context (company_id for multi-tenancy)
- User authentication already handled by Node.js
- Python trusts Node.js - no auth logic needed
- Future-proof for memory, RAG filtering, permissions

---

### 3. Response Format - Semantic Events ✅

**Before (UI-aware tokens):**
```json
{"token": "🔍 Querying database", "type": "tool_call"}
{"token": "There", "type": "final_answer"}
{"token": " are 10", "type": "final_answer"}
{"done": true, "metadata": {"reasoning_tokens": 5, "final_tokens": 10}}
```

**After (semantic events):**
```json
{"event": "tool_start", "tool": "sql_agent"}
{"event": "route_decision", "route": "sql"}
{"event": "token", "channel": "final", "content": "There"}
{"event": "token", "channel": "final", "content": " are 10"}
{"event": "complete", "stats": {"tokens": 15}}
```

**Why:**
- No UI concepts (emojis, labels) in Python
- Node.js owns UX mapping
- Easier to log, replay, evaluate
- Reusable for different frontends

---

### 4. Event Types

Python emits **5 semantic event types**:

#### `route_decision`
Agent's routing decision after classification.

```json
{
  "event": "route_decision",
  "route": "sql"  // or "rag"
}
```

#### `tool_start`
Tool execution beginning.

```json
{
  "event": "tool_start",
  "tool": "sql_agent"  // or "rag_agent"
}
```

#### `token`
Content token with channel context.

```json
{
  "event": "token",
  "channel": "final",  // or "sql_agent", "rag_agent", "classify"
  "content": "There are"
}
```

**Channels:**
- `classify`: Classification reasoning (usually skipped)
- `sql_agent`: SQL generation reasoning
- `rag_agent`: RAG retrieval reasoning
- `final`: Final answer to user

#### `complete`
Stream finished successfully.

```json
{
  "event": "complete",
  "stats": {
    "tokens": 42,
    "conversation_id": "conv-123"
  }
}
```

#### `error`
Error occurred during execution.

```json
{
  "event": "error",
  "error": "Database connection failed"
}
```

---

## Node.js Integration

### How Node.js Maps Events to UI

```javascript
// Node.js BFF layer (example)
async function streamChatToFrontend(req, res) {
  // 1. Authenticate user (cookies, JWT, etc.)
  const user = await authenticateUser(req);
  
  // 2. Call Python internal API
  const pythonResponse = await fetch('http://python-service:8000/internal/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      input: {
        message: req.body.message
      },
      conversation: {
        id: req.session.conversationId || uuidv4(),
        user_id: user.id,
        company_id: user.companyId
      }
    })
  });
  
  // 3. Map semantic events to UI tokens
  for await (const event of parseSSE(pythonResponse)) {
    if (event.event === 'tool_start') {
      // Add emojis and UI labels here
      if (event.tool === 'sql_agent') {
        sendToFrontend({ token: '🔍 Querying database', type: 'tool_call' });
      } else if (event.tool === 'rag_agent') {
        sendToFrontend({ token: '📚 Searching knowledge base', type: 'tool_call' });
      }
    }
    
    else if (event.event === 'token') {
      if (event.channel === 'final') {
        // Final answer - main chat bubble
        sendToFrontend({ token: event.content, type: 'final_answer' });
      } else {
        // Reasoning - show in "thinking" bubble or skip
        sendToFrontend({ token: event.content, type: 'reasoning' });
      }
    }
    
    else if (event.event === 'complete') {
      sendToFrontend({ done: true, metadata: event.stats });
    }
    
    else if (event.event === 'error') {
      sendToFrontend({ token: event.error, type: 'error' });
    }
  }
}
```

### SSE Proxy (Already Correct ✅)

Your existing Node.js SSE proxy is perfect:

```javascript
// ✅ Correct - forward raw chunks without parsing
app.post('/api/chat/stream', async (req, res) => {
  const pythonStream = await fetch('http://python:8000/internal/chat/stream', {
    method: 'POST',
    body: JSON.stringify({
      input: { message: req.body.message },
      conversation: {
        id: req.session.conversationId,
        user_id: req.user.id,
        company_id: req.user.companyId
      }
    })
  });
  
  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();
  
  // Forward chunks directly
  for await (const chunk of pythonStream.body) {
    res.write(chunk);
  }
  
  res.end();
});
```

---

## What Was Removed from Python

❌ **Removed:**
- Emojis ("🔍 Querying database", "📚 Searching knowledge base")
- UI-specific token types ("reasoning", "final_answer", "tool_call")
- Frontend-aware labels ("[Using SQLQueryAgent]")
- Comments about UI rendering

✅ **What Remains:**
- Agent orchestration logic
- LangGraph workflow
- Semantic event emission
- Token streaming
- Error handling

---

## Testing

### Test the Internal API

```bash
# Start the API server
cd apps/backend
uv run python run_api.py

# In another terminal, test with the new contract
uv run python test_internal_api.py
```

### Manual curl Test

```bash
curl -N -X POST http://localhost:8000/internal/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "message": "How many technicians are active?"
    },
    "conversation": {
      "id": "conv-test-123",
      "user_id": "user-456",
      "company_id": "company-789"
    }
  }'
```

**Expected output:**
```
data: {"event":"tool_start","tool":"sql_agent"}
data: {"event":"route_decision","route":"sql"}
data: {"event":"token","channel":"final","content":"There"}
data: {"event":"token","channel":"final","content":" are"}
data: {"event":"token","channel":"final","content":" 10"}
...
data: {"event":"complete","stats":{"tokens":42}}
```

---

## API Documentation

FastAPI auto-generates Swagger docs at:
```
http://localhost:8000/docs
```

The docs now clearly show this is an **internal API** with the `/internal/*` prefix.

---

## Benefits

### 1. **Clean Separation**
- Python = Agent logic only
- Node.js = Auth + UX mapping
- No UI concerns leak into AI layer

### 2. **Reusable**
- Same Python service can serve multiple frontends
- Mobile apps, web apps, CLI tools all use same semantic events
- Node.js controls UX without redeploying Python

### 3. **Security**
- No authentication logic in Python
- Python trusts Node.js (internal network only)
- Easier to secure with network policies

### 4. **Observability**
- Semantic events easier to log
- Can replay conversations from raw events
- Better debugging and evaluation

### 5. **Future-Proof**
- Easy to add new event types
- Node.js adapts UX without breaking Python
- Supports A/B testing different UX styles

---

## Next Steps (Phase 6)

With the internal API established, the next phase can add:

1. **Conversation Memory**
   - Load message history using `conversation.id`
   - LangGraph checkpointing
   - SQL-backed memory store

2. **Multi-Tenancy**
   - Use `conversation.company_id` for data isolation
   - Tenant-specific RAG collections
   - Company-specific SQL schemas

3. **User Context**
   - Use `conversation.user_id` for permissions
   - User-specific document access
   - Personalized responses

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Endpoint** | `/api/chat/stream` | `/internal/chat/stream` |
| **Request** | `{message, conversation_id?}` | `{input, conversation}` |
| **Response** | UI tokens with types | Semantic events |
| **Auth** | None (assumed frontend) | Trusted from Node.js |
| **UX Logic** | In Python (emojis, labels) | In Node.js only |
| **Reusability** | Frontend-specific | Multi-frontend ready |

**Result:** Clean, production-ready internal API that focuses solely on agent orchestration. 🎉
