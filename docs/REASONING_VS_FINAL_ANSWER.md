# Reasoning vs Final Answer - Streaming Strategy

## 🎯 Problem

How to differentiate between:
- **Reasoning tokens** (SQL generation, classification, thinking)
- **Final answer tokens** (the actual response to the user)

So the frontend can:
1. Show reasoning in a separate "thinking..." bubble (different color)
2. Replace reasoning bubble with only the latest reasoning
3. Remove reasoning when final answer arrives
4. Show final answer as the main response

## ✅ Solution: Node-Based Token Tagging

### How It Works

The OrchestratorAgent has this workflow:
```
classify → [sql_agent OR rag_agent] → finalize
```

**Key Insight**: Each streaming token comes from a specific node!

- **Nodes**: `classify`, `sql_agent`, `rag_agent` → **Type**: `"reasoning"`
- **Node**: `finalize` → **Type**: `"final_answer"`

### Updated Token Types

```python
class ChatToken(BaseModel):
    token: str
    type: Literal["reasoning", "final_answer", "tool_call", "error"]
```

| Type | Description | Frontend Display |
|------|-------------|------------------|
| **`reasoning`** | Classification, SQL generation, RAG thinking | Gray bubble, replace on update |
| **`final_answer`** | The actual response to user | Main chat bubble |
| **`tool_call`** | Route decisions: "🔍 Querying database" or "📚 Searching knowledge base" | Badge/pill/icon (like GitHub Copilot) |
| **`error`** | Error messages | Red error bubble |

## 📊 Example Stream

### Request
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "How many technicians are active?"}'
```

### Response Flow

```
# Phase 1: Route decision (as tool_call)
data: {"token":"🔍 Querying database","type":"tool_call"}

# Phase 2: Reasoning (SQL query generation)
data: {"token":"SELECT","type":"reasoning"}
data: {"token":" COUNT","type":"reasoning"}
...

# Phase 3: Final answer!
data: {"token":"There","type":"final_answer"}
data: {"token":" are","type":"final_answer"}
data: {"token":" 10","type":"final_answer"}
data: {"token":" active","type":"final_answer"}
data: {"token":" technicians","type":"final_answer"}
data: {"token":".","type":"final_answer"}

# Completion
data: {"done":true,"metadata":{"tokens_sent":28,"reasoning_tokens":22,"final_tokens":6}}
```

## 💻 Frontend Implementation Guide

### React Example with EventSource

```typescript
import { useEffect, useState } from 'react';

interface Message {
  reasoning: string;
  final: string;
  route: string;  // "🔍 Querying database" or "📚 Searching knowledge base"
  isComplete: boolean;
}

function ChatStream({ message }: { message: string }) {
  const [response, setResponse] = useState<Message>({
    reasoning: '',
    final: '',
    route: '',
    isComplete: false
  });

  useEffect(() => {
    const eventSource = new EventSource(
      `http://localhost:8000/api/chat/stream?message=${encodeURIComponent(message)}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.done) {
        setResponse(prev => ({ ...prev, isComplete: true }));
        eventSource.close();
        return;
      }

      const { token, type } = data;

      if (type === 'tool_call') {
        // Show route decision as a badge
        setResponse(prev => ({
          ...prev,
          route: token
        }));
      } else if (type === 'reasoning') {
        // Accumulate reasoning tokens
        setResponse(prev => ({
          ...prev,
          reasoning: prev.reasoning + token
        }));
      } else if (type === 'final_answer') {
        // Accumulate final answer tokens
        setResponse(prev => ({
          ...prev,
          final: prev.final + token
        }));
      }
    };

    return () => eventSource.close();
  }, [message]);

  return (
    <div>
      {/* Route badge - shown immediately */}
      {response.route && (
        <div className="route-badge bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm inline-flex items-center gap-2 mb-2">
          <span>{response.route}</span>
        </div>
      )}

      {/* Reasoning bubble - hide when final answer appears */}
      {response.reasoning && !response.final && (
        <div className="reasoning-bubble bg-gray-100 text-gray-600 p-3 rounded">
          <span className="text-xs">🤔 Thinking...</span>
          <pre className="text-sm mt-2 whitespace-pre-wrap">{response.reasoning}</pre>
        </div>
      )}

      {/* Final answer bubble */}
      {response.final && (
        <div className="answer-bubble bg-blue-500 text-white p-3 rounded">
          {response.final}
        </div>
      )}

      {/* Optional: Show reasoning as expandable after final answer */}
      {response.final && response.isComplete && response.reasoning && (
        <details className="mt-2">
          <summary className="text-xs text-gray-500 cursor-pointer">
            View reasoning
          </summary>
          <pre className="text-xs text-gray-600 mt-2 whitespace-pre-wrap">{response.reasoning}</pre>
        </details>
      )}
    </div>
  );
}
```

### Alternative: Replace Strategy

```typescript
function ChatStream({ message }: { message: string }) {
  const [reasoning, setReasoning] = useState('');
  const [final, setFinal] = useState('');
  const [showReasoning, setShowReasoning] = useState(true);

  useEffect(() => {
    const eventSource = new EventSource(/* ... */);

    eventSource.onmessage = (event) => {
      const { token, type } = JSON.parse(event.data);

      if (type === 'reasoning') {
        setReasoning(prev => prev + token);
      } else if (type === 'final_answer') {
        // Hide reasoning when final answer starts
        setShowReasoning(false);
        setFinal(prev => prev + token);
      }
    };

    return () => eventSource.close();
  }, [message]);

  return (
    <>
      {showReasoning && reasoning && (
        <div className="thinking-bubble animate-pulse">
          🤔 Thinking...
        </div>
      )}
      {final && <div className="answer-bubble">{final}</div>}
    </>
  );
}
```

## 🎨 UX Patterns

### Pattern 1: Replace on Final Answer
```
[Reasoning bubble showing "SQL..."] 
         ↓ (final answer arrives)
[Final answer bubble: "There are 10..."]
```

### Pattern 2: Keep Reasoning Collapsed
```
[Final answer: "There are 10 technicians"]
[Details ▼ View reasoning]  ← Expandable
```

### Pattern 3: Side-by-side
```
┌─────────────────────┐
│ 🤔 Reasoning        │
│ SQL query...        │
└─────────────────────┘

┌─────────────────────┐
│ ✅ Answer           │
│ There are 10...     │
└─────────────────────┘
```

## 🔧 Backend Implementation Details

### Detection Logic

```python
# In stream_orchestrator_response()
if event["event"] == "on_chat_model_stream":
    event_name = event.get("name", "")
    event_tags = event.get("tags", [])
    
    # Finalize node = final answer
    if "finalize" in event_name.lower() or "finalize" in str(event_tags):
        token_type = "final_answer"
    else:
        # Everything else = reasoning
        token_type = "reasoning"
```

### Metadata Tracking

The completion event includes breakdown:
```json
{
  "done": true,
  "metadata": {
    "tokens_sent": 28,
    "reasoning_tokens": 22,
    "final_tokens": 6
  }
}
```

This helps frontend:
- Show progress indicators
- Estimate completion
- Debug issues

## 🧪 Testing

### Test Command
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "How many jobs are in progress?"}'
```

### Expected Output
```
# Reasoning phase
data: {"token":"SQL","type":"reasoning"}
data: {"token":"```sql\nSELECT...","type":"reasoning"}

# Tool marker
data: {"token":"[Using SQLQueryAgent]","type":"tool_call"}

# Final answer phase
data: {"token":"There","type":"final_answer"}
data: {"token":" are","type":"final_answer"}
...
```

## 🎯 Benefits of This Approach

### ✅ Clean Separation
- Backend automatically tags tokens by workflow node
- No complex frontend logic needed
- Type-safe with Pydantic validation

### ✅ Flexible UX
Frontend can choose to:
- Show reasoning or hide it
- Replace reasoning with final answer
- Keep reasoning expandable
- Animate transitions

### ✅ Transparent AI
Users can see:
- What the AI is thinking
- SQL queries being generated
- Tools being used
- Full reasoning chain

### ✅ Debuggable
- Metadata shows token counts
- Easy to identify which node is slow
- Can add more granular types later

## 🔮 Future Enhancements

### More Token Types
```python
type: Literal[
    "classification",    # Classification reasoning
    "sql_generation",    # SQL query generation
    "rag_retrieval",     # RAG retrieval thinking
    "final_answer",      # Final response
    "tool_call",         # Tool execution
    "error"              # Errors
]
```

### Node-Specific Metadata
```json
{
  "token": "SELECT COUNT(*)",
  "type": "sql_generation",
  "metadata": {
    "node": "sql_agent",
    "step": 2
  }
}
```

### Streaming States
```json
{
  "state": "thinking",
  "phase": "classification"
}
```

## 📝 Summary

### What Changed

1. **Updated `ChatToken` model** - New token types: `reasoning`, `final_answer`, `tool_call`, `error`
2. **Enhanced streaming logic** - Detects which node is streaming and tags accordingly
3. **Added metadata** - Completion event includes token counts breakdown
4. **Enabled tool markers** - Optional `[Using X]` markers for tool execution

### Frontend Integration

```typescript
// Simple pattern
if (type === 'reasoning') {
  showInThinkingBubble(token);
} else if (type === 'final_answer') {
  hideThinkingBubble();
  showInAnswerBubble(token);
}
```

### API Contract

**No breaking changes!** Existing clients still work, new clients can leverage token types.

---

**Ready to test!** 🚀 The API now supports rich UX patterns for showing AI reasoning.
