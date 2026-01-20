# Field Service Intelligence Agent (FSIA) - Project Plan

> **Learning Project**: Master LangGraph, RAG, embeddings, chunking, memory, and tool orchestration through a real-world agentic system.

## 🎯 Project Overview

Build a reasoning agent embedded in a field-service web app that **explains, audits, and assists** with operational data using RAG + LangGraph workflows.

### What Users Can Ask

- "Why can't this employee register more hours on Tuesday?"
- "Explain why this job went over budget."
- "Which scheduling rule was violated here?"
- "What documents are missing for this expense?"

### What Makes This Different

This is **not just Q&A**. The agent:
- ✅ Retrieves data from multiple sources (SQL + Vector DB + Rules)
- ✅ Applies business logic and constraints
- ✅ Explains reasoning step-by-step
- ✅ Proposes corrective actions
- ✅ Maintains conversation context

---

## 📚 Learning Objectives Mapping

| Learning Objective | Where You'll Apply It |
|-------------------|----------------------|
| **LangGraph workflows** | Multi-step reasoning chains, decision trees, conditional routing |
| **RAG patterns** | SQL data + document embeddings + rule retrieval |
| **Memory management** | Conversation history + entity memory + user preferences |
| **Embeddings & chunking** | Work descriptions, receipts, policy docs, logs |
| **Tool orchestration** | SQL queries, vector search, rule engines, API calls |
| **Production patterns** | Error handling, retries, guardrails, observability |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Frontend                            │
│              (React/Next.js with AI Panel)                  │
└──────────────────┬──────────────────────────────────────────┘
                   │ API Request + Page Context
                   ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           LangGraph Agent Workflow                   │   │
│  │                                                      │   │
│  │  User Question                                       │   │
│  │       ↓                                              │   │
│  │  Intent Classification                               │   │
│  │       ↓                                              │   │
│  │  Entity Extraction (employee, job, date)             │   │
│  │       ↓                                              │   │
│  │  Parallel Retrieval                                  │   │
│  │    ├─ SQL Tool (structured data)                     │   │
│  │    ├─ Vector Search (policies, descriptions)         │   │
│  │    └─ Rule Lookup (constraints)                      │   │
│  │       ↓                                              │   │
│  │  Reasoning Node (apply rules + validate)             │   │
│  │       ↓                                              │   │
│  │  Explanation Generator (natural language)            │   │
│  │       ↓                                              │   │
│  │  Action Suggestions (next steps)                     │   │
│  └──────────────────────────────────────────────────────┘   │
└───────┬──────────────┬──────────────┬──────────────┬─────────┘
        │              │              │              │
   ┌────▼────┐   ┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
   │ SQLite/ │   │  ChromaDB │  │   Rule   │  │  Memory  │
   │Postgres │   │  (Vector  │  │  Engine  │  │  Store   │
   │   DB    │   │   Store)  │  │  (YAML)  │  │  (Redis) │
   └─────────┘   └───────────┘  └──────────┘  └──────────┘
```

---

## 🗄️ Domain Model

### Core Entities (SQL Database)

```python
# Technician Table
- id: str
- name: str
- skills: List[str]
- contract_type: str (full_time, part_time, contractor)
- max_daily_hours: int
- max_weekly_hours: int
- hourly_rate: float

# Job Table
- id: str
- customer_id: str
- site_location: str
- scheduled_start: datetime
- scheduled_end: datetime
- required_skills: List[str]
- status: str (pending, in_progress, completed)
- budget: float

# WorkLog Table
- id: str
- technician_id: str
- job_id: str
- date: date
- hours_logged: float
- description: str (long text - embedded)
- approved: bool

# Expense Table
- id: str
- job_id: str
- type: str (materials, travel, equipment)
- amount: float
- receipt_text: str (OCR text - embedded)
- status: str (pending, approved, rejected)
- submitted_date: datetime

# ScheduleRule Table
- id: str
- rule_name: str
- rule_description: str (embedded)
- severity: str (error, warning, info)
```

### Knowledge Layers

| Layer | Data Type | Storage | Retrieval Method |
|-------|-----------|---------|------------------|
| **Structured** | Hours, schedules, contracts | SQL Database | SQL queries via tool |
| **Unstructured** | Work descriptions, receipts, policies | ChromaDB | Vector similarity search |
| **Rules** | Scheduling constraints, compliance | YAML + ChromaDB | Hybrid (exact + semantic) |

---

## 🔄 Agent Workflow Example

**User Question**: _"Why can't John register 3 more hours on Friday?"_

### Step-by-Step Execution

```
1️⃣ Intent Classification
   → Type: "schedule_validation"
   → Entities: {technician: "John", date: "Friday", hours: 3}

2️⃣ Parallel Retrieval
   ┌─ SQL Tool: Get John's existing hours on Friday
   │  Query: SELECT SUM(hours_logged) FROM work_logs 
   │         WHERE technician_id = 'john' AND date = '2026-01-24'
   │  Result: 7 hours
   │
   ├─ SQL Tool: Get John's contract limits
   │  Query: SELECT max_daily_hours FROM technician WHERE id = 'john'
   │  Result: 8 hours/day
   │
   └─ Vector Search: Relevant scheduling rules
      Query: "overtime registration rules"
      Results: [
        "Daily hours cannot exceed contract limits",
        "Overtime requires manager approval",
        "Weekend hours count as 1.5x regular"
      ]

3️⃣ Reasoning Node
   - Current hours: 7
   - Requested hours: 3
   - Daily limit: 8
   - Calculation: 7 + 3 = 10 > 8 ❌
   - Rule violated: "max_daily_hours"

4️⃣ Explanation Generator
   "John has already logged 7 hours on Friday. His contract 
    limits daily work to 8 hours, so only 1 additional hour 
    can be registered without overtime approval."

5️⃣ Action Suggestions
   - "Reduce entry to 1 hour"
   - "Request overtime approval from manager"
   - "Move 2 hours to Saturday (weekend rate applies)"
```

---

## 🛠️ Tech Stack

### Infrastructure (Already Set Up ✅)
- **Nx Monorepo** - Workspace management
- **Node.js 20.19.6** - JavaScript runtime
- **Python 3.11** - Backend language
- **UV Package Manager** - Fast dependency management

### AI/ML Stack
- **LangChain** - Agent framework
- **LangGraph** - Workflow orchestration & memory
- **OpenAI GPT-4o-mini** - LLM for reasoning
- **ChromaDB** - Vector database for RAG
- **Sentence Transformers** - Text embeddings

### Backend
- **FastAPI** - API server
- **SQLite/PostgreSQL** - Structured data
- **Pydantic** - Data validation
- **SQLAlchemy** - ORM

### Frontend
- **React/Next.js** - Web interface
- **TailwindCSS** - Styling
- **React Query** - State management

### Tools & Patterns
- **MCP (Model Context Protocol)** - Standardized tool interfaces
- **Redis** - Memory/cache (optional)
- **Loguru** - Structured logging

---

## 📋 Implementation Phases

### Phase 0: Foundation Setup ✅
**Status**: Complete

**What We Have**:
- Nx monorepo structure
- Python environment with UV
- LangChain & LangGraph installed
- Configuration management
- Logging utilities

---

### Phase 1: Domain Model & Mock Data
**Goal**: Create realistic database schema and sample data

**Tasks**:
- [ ] Design SQLAlchemy models (Technician, Job, WorkLog, Expense)
- [ ] Create database migration scripts
- [ ] Generate mock data (10 technicians, 50 jobs, 200 work logs)
- [ ] Add realistic constraints and edge cases
- [ ] Create simple CRUD API endpoints

**Tools**:
- SQLAlchemy
- Faker (for mock data)
- Alembic (migrations)
- FastAPI

**Deliverable**: Populated database with realistic field service data

---

### Phase 2: Basic RAG - SQL Tool Integration
**Goal**: Build the first tool - SQL query agent

**Tasks**:
- [ ] Create SQL query tool using LangChain SQLDatabaseToolkit
- [ ] Implement safe query validation (read-only, no DROP/DELETE)
- [ ] Build simple question → SQL → answer flow
- [ ] Handle errors gracefully
- [ ] Log all queries for debugging

**Learning Focus**: Tool creation, error handling, SQL safety

**Tools**:
- LangChain SQLDatabaseToolkit
- LangGraph (single node workflow)
- Pydantic for validation

**Example Questions**:
- "How many hours did John work this week?"
- "What jobs are scheduled for tomorrow?"
- "Show me all pending expenses"

**Deliverable**: Working SQL query agent with basic Q&A

---

### Phase 3: Vector Store - Unstructured Data
**Goal**: Add semantic search for policies and descriptions

**Tasks**:
- [ ] Set up ChromaDB collection
- [ ] Create chunking strategy for different document types:
  - Work descriptions (semantic chunking)
  - Policy documents (rule-per-chunk)
  - Receipt text (line-based)
- [ ] Embed sample policy documents
- [ ] Embed work log descriptions
- [ ] Build vector search tool
- [ ] Test retrieval quality

**Learning Focus**: Embeddings, chunking strategies, vector search

**Tools**:
- ChromaDB
- Sentence Transformers (all-MiniLM-L6-v2)
- LangChain text splitters

**Chunking Example**:
```python
# Policy Document
chunk_strategy = "rule_per_chunk"
chunks = [
  "Daily hours cannot exceed contract limits",
  "Overtime requires manager approval",
  "Weekend hours count as 1.5x regular"
]

# Work Description
chunk_strategy = "semantic"
chunks = RecursiveCharacterTextSplitter(
  chunk_size=500,
  chunk_overlap=50
).split_text(description)
```

**Deliverable**: Vector store with searchable policies and descriptions

---

### Phase 4: LangGraph Multi-Step Workflow
**Goal**: Orchestrate multiple tools in a reasoning chain

**Tasks**:
- [ ] Design state schema (conversation + entities + retrieved data)
- [ ] Build intent classification node
- [ ] Build entity extraction node
- [ ] Create parallel retrieval node (SQL + Vector + Rules)
- [ ] Implement reasoning node
- [ ] Add explanation generator node
- [ ] Create action suggestion node
- [ ] Add conditional routing (different paths for different intents)

**Learning Focus**: LangGraph workflows, state management, parallel execution

**Workflow Graph**:
```python
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)

# Add nodes
graph.add_node("classify_intent", classify_intent_node)
graph.add_node("extract_entities", extract_entities_node)
graph.add_node("retrieve_data", parallel_retrieval_node)
graph.add_node("apply_rules", reasoning_node)
graph.add_node("generate_explanation", explanation_node)
graph.add_node("suggest_actions", action_node)

# Add edges (workflow)
graph.set_entry_point("classify_intent")
graph.add_edge("classify_intent", "extract_entities")
graph.add_edge("extract_entities", "retrieve_data")
graph.add_edge("retrieve_data", "apply_rules")
graph.add_edge("apply_rules", "generate_explanation")
graph.add_edge("generate_explanation", "suggest_actions")
graph.add_edge("suggest_actions", END)

workflow = graph.compile()
```

**Example State**:
```python
class AgentState(TypedDict):
    question: str
    intent: str
    entities: Dict[str, Any]
    sql_data: List[Dict]
    vector_results: List[str]
    rules: List[str]
    reasoning: str
    explanation: str
    actions: List[str]
    messages: List[BaseMessage]
```

**Deliverable**: Multi-step reasoning workflow with parallel retrieval

---

### Phase 5: Memory Management
**Goal**: Add conversation and entity memory

**Tasks**:
- [ ] Implement conversation memory (recent messages)
- [ ] Add entity memory (selected technician/job persists)
- [ ] Build user preference memory (technical vs simple answers)
- [ ] Create memory retrieval node
- [ ] Test multi-turn conversations
- [ ] Add memory summarization (compress old messages)

**Learning Focus**: LangGraph memory, context windows, summarization

**Memory Types**:
```python
# Short-term: Conversation buffer
conversation_memory = ConversationBufferMemory(
    return_messages=True,
    memory_key="chat_history"
)

# Long-term: Entity memory
entity_memory = {
    "current_technician": "john_doe",
    "current_job": "job_123",
    "user_preference": "technical"
}

# LangGraph Checkpointing
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string("checkpoints.db")
workflow = graph.compile(checkpointer=memory)
```

**Example Multi-Turn**:
```
User: "Show me John's hours this week"
Agent: [retrieves data] "John logged 32 hours..."

User: "Can he work 5 more hours on Friday?"
Agent: [uses entity_memory: John] "John already has..."
```

**Deliverable**: Stateful conversations with entity tracking

---

### Phase 6: Rule Engine & Validation
**Goal**: Formalize business rules and constraint checking

**Tasks**:
- [ ] Design rule schema (YAML or JSON)
- [ ] Implement rule evaluation engine
- [ ] Add rule categories (scheduling, budgets, compliance)
- [ ] Embed rule descriptions in vector store
- [ ] Create rule conflict detection
- [ ] Build rule explanation generator

**Learning Focus**: Hybrid retrieval (exact + semantic), rule-based reasoning

**Rule Schema**:
```yaml
# scheduling_rules.yaml
rules:
  - id: max_daily_hours
    name: "Maximum Daily Hours"
    description: "Technicians cannot exceed their contract's daily hour limit"
    type: hard_constraint
    validation:
      field: hours_logged
      operator: sum_per_day
      threshold: contract.max_daily_hours
    severity: error
    
  - id: skill_match
    name: "Required Skills Match"
    description: "Assigned technician must have all required job skills"
    type: hard_constraint
    validation:
      field: technician.skills
      operator: contains_all
      threshold: job.required_skills
    severity: error
    
  - id: budget_warning
    name: "Budget Threshold Warning"
    description: "Warn when job expenses exceed 80% of budget"
    type: soft_constraint
    validation:
      field: expenses
      operator: sum_percentage
      threshold: 0.8
    severity: warning
```

**Rule Engine**:
```python
class RuleEngine:
    def evaluate(self, rule: Rule, context: Dict) -> RuleResult:
        """Evaluate a rule against current context"""
        
    def explain_violation(self, rule: Rule, context: Dict) -> str:
        """Generate natural language explanation"""
        
    def suggest_fix(self, rule: Rule, context: Dict) -> List[Action]:
        """Propose corrective actions"""
```

**Deliverable**: Rule-based validation with explanations

---

### Phase 7: MCP (Model Context Protocol)
**Goal**: Standardize tool interfaces and context management

**Tasks**:
- [ ] Define MCP tool schemas
- [ ] Implement context providers
- [ ] Add parameter validation
- [ ] Create tool registry
- [ ] Build tool execution middleware
- [ ] Add tool call logging and observability

**Learning Focus**: Tool abstraction, context control, production patterns

**MCP Tool Example**:
```python
from typing import TypedDict
from pydantic import BaseModel, Field

class GetWorkLogsInput(BaseModel):
    """Input schema for work log retrieval"""
    technician_id: str = Field(description="Technician ID")
    date: str = Field(description="Date in YYYY-MM-DD format")
    
class GetWorkLogsTool:
    name = "get_work_logs"
    description = "Retrieve work logs for a technician on a specific date"
    input_schema = GetWorkLogsInput
    
    def execute(self, params: GetWorkLogsInput) -> Dict:
        # Validated, typed execution
        logs = db.query(WorkLog).filter(
            WorkLog.technician_id == params.technician_id,
            WorkLog.date == params.date
        ).all()
        return {"logs": [log.to_dict() for log in logs]}

# Tool Registry
tools = ToolRegistry()
tools.register(GetWorkLogsTool())
tools.register(GetScheduleRulesTool())
tools.register(VectorSearchTool())
```

**Context Provider**:
```python
class PageContextProvider:
    """Extracts context from web page state"""
    
    def get_context(self, page: str, page_data: Dict) -> Dict:
        if page == "technician_detail":
            return {
                "technician_id": page_data["id"],
                "technician_name": page_data["name"]
            }
        elif page == "job_detail":
            return {
                "job_id": page_data["id"],
                "customer": page_data["customer"]
            }
```

**Deliverable**: Standardized tool system with MCP

---

### Phase 8: Web Integration
**Goal**: Embed agent in a real web application

**Tasks**:
- [ ] Build FastAPI endpoints for agent queries
- [ ] Create React chat component
- [ ] Add context-aware prompts (pre-fill from page)
- [ ] Implement streaming responses
- [ ] Add loading states and error handling
- [ ] Build "Explain" button on data tables
- [ ] Add conversation history UI

**Learning Focus**: API design, frontend integration, UX patterns

**Frontend Components**:
```typescript
// AgentPanel.tsx
export function AgentPanel({ pageContext }: Props) {
  const { data, isLoading } = useAgentQuery({
    question: userInput,
    context: pageContext  // Auto-includes current technician/job
  })
  
  return (
    <div className="agent-panel">
      <ChatHistory messages={data.messages} />
      <Input 
        placeholder="Ask about this technician..." 
        context={pageContext}
      />
      <ActionButtons actions={data.suggested_actions} />
    </div>
  )
}

// Usage in Technician Detail Page
<TechnicianDetail id="john">
  <AgentPanel pageContext={{ 
    technician_id: "john",
    page: "technician_detail" 
  }} />
</TechnicianDetail>
```

**API Endpoints**:
```python
# FastAPI Backend
@app.post("/api/agent/query")
async def query_agent(request: AgentRequest):
    """
    Main agent endpoint
    - Receives question + page context
    - Runs LangGraph workflow
    - Returns explanation + actions
    """
    result = await workflow.ainvoke({
        "question": request.question,
        "page_context": request.context,
        "user_id": request.user_id
    })
    
    return AgentResponse(
        explanation=result["explanation"],
        actions=result["actions"],
        reasoning_steps=result["reasoning"],
        sources=result["sources"]
    )

@app.get("/api/agent/stream")
async def stream_agent(question: str):
    """Stream agent responses token by token"""
    async for chunk in workflow.astream({"question": question}):
        yield f"data: {json.dumps(chunk)}\n\n"
```

**Deliverable**: Web app with embedded AI assistant

---

### Phase 9: Production Patterns
**Goal**: Add observability, error handling, and guardrails

**Tasks**:
- [ ] Implement comprehensive logging (all agent steps)
- [ ] Add LangSmith tracing integration
- [ ] Build retry logic for failed tool calls
- [ ] Create "I don't know" detection
- [ ] Add hallucination guardrails
- [ ] Implement rate limiting
- [ ] Add monitoring dashboards
- [ ] Create error recovery flows

**Learning Focus**: Production readiness, observability, reliability

**Observability Stack**:
```python
from langsmith import traceable
from loguru import logger

@traceable(name="agent_workflow")
async def run_agent(question: str):
    """Fully traced agent execution"""
    
    try:
        # Log input
        logger.info("Agent query", question=question)
        
        # Run with tracing
        result = await workflow.ainvoke({"question": question})
        
        # Log output
        logger.success("Agent response", 
                      explanation=result["explanation"],
                      actions_count=len(result["actions"]))
        
        return result
        
    except ToolExecutionError as e:
        # Retry with exponential backoff
        logger.warning("Tool failed, retrying", error=str(e))
        await asyncio.sleep(2 ** attempt)
        
    except Exception as e:
        # Graceful degradation
        logger.error("Agent failed", error=str(e))
        return {
            "explanation": "I encountered an error. Please try again.",
            "error": True
        }
```

**Guardrails**:
```python
class HallucinationGuard:
    """Prevent agent from inventing data"""
    
    def validate(self, response: str, retrieved_data: Dict) -> bool:
        # Check if response contains facts not in retrieved data
        # Use NLI model or rule-based checking
        
class ConfidenceThreshold:
    """Require minimum confidence for answers"""
    
    def should_respond(self, confidence: float) -> bool:
        if confidence < 0.7:
            return False  # Say "I don't know"
        return True
```

**Deliverable**: Production-ready agent with monitoring

---

## 🎓 Learning Milestones

After completing each phase, you will have learned:

| Phase | Key Skills Acquired |
|-------|---------------------|
| **1** | Database design, mock data generation, domain modeling |
| **2** | Tool creation, SQL safety, basic RAG, error handling |
| **3** | Embeddings, chunking strategies, vector search, similarity |
| **4** | LangGraph workflows, state management, parallel execution |
| **5** | Memory systems, context windows, multi-turn conversations |
| **6** | Rule engines, hybrid retrieval, constraint validation |
| **7** | Tool abstraction, MCP protocol, production patterns |
| **8** | API design, frontend integration, streaming, UX |
| **9** | Observability, tracing, guardrails, reliability |

---

## 🚀 Getting Started

1. **Review Phase 0** - Ensure infrastructure is working
   ```bash
   npm run backend:start
   ```

2. **Start Phase 1** - Set up domain model
   ```bash
   cd apps/backend
   # Create models, migrations, mock data
   ```

3. **Track Progress** - Use this document as your roadmap
   - Check off tasks as you complete them
   - Document learnings in `docs/LEARNINGS.md`
   - Save code examples in `docs/examples/`

---

## 📊 Success Criteria

You'll know you've succeeded when you can:

✅ Explain the difference between structured and unstructured knowledge retrieval  
✅ Design a multi-step LangGraph workflow from scratch  
✅ Choose appropriate chunking strategies for different data types  
✅ Implement conversation memory and entity tracking  
✅ Build production-ready tools with MCP  
✅ Debug agent failures using observability tools  
✅ Embed an AI agent in a web application  
✅ Interview confidently about real agentic systems  

---

## 🎯 Why This Project Is Perfect

This isn't a toy chatbot. You're building a **reasoning system** that:

- Combines multiple data sources intelligently
- Applies business logic transparently
- Explains its reasoning step-by-step
- Proposes actionable solutions
- Maintains conversation context
- Handles errors gracefully

**This is exactly what companies building with CrewOS, LangGraph, and production AI agents are doing.**

---

## 📚 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)

---

**Ready to start? Begin with Phase 1: Domain Model & Mock Data**
