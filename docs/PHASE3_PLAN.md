# Phase 3: Vector Store & RAG - Detailed Learning Plan

## 🎯 Learning Objectives

By the end of Phase 3, you will deeply understand:

- **Chunking Strategies**: When to use character-based, semantic, or document-structure chunking
- **Embeddings**: How vector representations work, trade-offs between models
- **Vector Databases**: How similarity search works, indexing strategies
- **RAG Patterns**: Naive RAG → Advanced RAG with reranking and hybrid search
- **Production Considerations**: Chunk size optimization, caching, latency

---

## 📚 Phase 3 Overview

**Goal**: Enable semantic search over unstructured text data (work descriptions, receipts, rules) to complement the SQL agent from Phase 2.

**Why It Matters**: SQL is great for structured queries ("How many jobs?"), but fails for conceptual questions ("Show me jobs where the customer complained about quality"). Vector search bridges this gap.

**Current Data Ready for Embedding**:
1. **Work Log Descriptions** (200 entries) - Narrative text about work performed
2. **Expense Receipt Text** (100 entries) - OCR text from receipts
3. **Schedule Rule Descriptions** (10 entries) - Business rules in natural language

---

## 🗺️ Phase 3 Roadmap: Choose Your Path

### **Path A: Fundamentals Track** (Recommended for Learning)
*Best for understanding core concepts deeply*

**Focus**: Learn chunking → embeddings → basic RAG → optimize

**Timeline**: 4-6 hours of implementation + experimentation

**Tools**:
- Chunking: LangChain's `RecursiveCharacterTextSplitter`
- Embeddings: OpenAI `text-embedding-3-small` (simple, fast)
- Vector DB: ChromaDB (local, no setup needed)
- RAG: Naive RAG (retrieve → stuff into prompt)

**Outcome**: Solid foundation, understand trade-offs, ready to advance

---

### **Path B: Production-Ready Track** (Advanced)
*Best for building real-world systems*

**Focus**: Advanced chunking → hybrid embeddings → optimized RAG

**Timeline**: 8-10 hours

**Tools**:
- Chunking: Semantic chunking + metadata filtering
- Embeddings: OpenAI + local model for hybrid search
- Vector DB: ChromaDB with persistent storage + indexing
- RAG: Hybrid search (vector + keyword) + reranking

**Outcome**: Production-grade RAG system with advanced patterns

---

### **Path C: Experimentation Track** (Exploratory)
*Best for comparing different approaches*

**Focus**: Compare multiple tools/strategies side-by-side

**Timeline**: 6-8 hours

**Tools**: Try multiple options for each component
- Chunking: Test 3 strategies (character, semantic, recursive)
- Embeddings: Compare OpenAI vs Sentence Transformers
- Vector DB: ChromaDB vs FAISS
- RAG: A/B test naive vs advanced patterns

**Outcome**: Hands-on experience, data to make informed decisions

---

## 🧩 Component Breakdown: Options & Trade-offs

### **1. Chunking Strategies**

#### **Option 1A: Fixed-Size Character Chunking** ⭐ *Simplest*
```python
chunk_size = 500 characters
chunk_overlap = 50 characters
```
**Pros**: Simple, predictable, fast
**Cons**: May split sentences mid-thought, no semantic awareness
**Best for**: Short documents, experimentation

#### **Option 1B: Recursive Character Splitting** ⭐⭐ *Recommended*
```python
separators = ["\n\n", "\n", ". ", " ", ""]  # Try each in order
chunk_size = 500
overlap = 50
```
**Pros**: Respects document structure, splits on natural boundaries
**Cons**: Still no semantic understanding
**Best for**: Most use cases, good balance

#### **Option 1C: Semantic Chunking** ⭐⭐⭐ *Advanced*
```python
# Group sentences by semantic similarity
# Split when similarity drops below threshold
```
**Pros**: Keeps related content together, ideal for RAG
**Cons**: Slower, requires embedding each sentence first
**Best for**: Long documents, high-quality requirements

#### **Option 1D: Document-Structure Chunking**
```python
# Split by headers, paragraphs, sections
# Add metadata (section title, page number)
```
**Pros**: Preserves document hierarchy, great context
**Cons**: Requires structured documents (PDFs, HTML)
**Best for**: Technical docs, reports

---

### **2. Embedding Models**

#### **Option 2A: OpenAI Embeddings** ⭐⭐ *Recommended*
```python
model = "text-embedding-3-small"
dimensions = 1536
cost = $0.02 / 1M tokens
```
**Pros**: High quality, low latency, well-tested
**Cons**: Costs money, requires API key, data leaves server
**Best for**: Production apps, when quality matters

#### **Option 2B: OpenAI Large Model** ⭐⭐⭐ *Highest Quality*
```python
model = "text-embedding-3-large"
dimensions = 3072 (configurable)
cost = $0.13 / 1M tokens
```
**Pros**: Best quality, supports shortening dimensions
**Cons**: More expensive, larger storage
**Best for**: High-stakes retrieval, when budget allows

#### **Option 2C: Sentence Transformers (Local)** ⭐ *Free*
```python
model = "all-MiniLM-L6-v2"
dimensions = 384
cost = Free (runs locally)
```
**Pros**: Free, private, offline-capable, fast
**Cons**: Lower quality than OpenAI, larger model files
**Best for**: Prototypes, privacy-sensitive data, cost-conscious

#### **Option 2D: Hybrid Embeddings** ⭐⭐⭐ *Advanced*
```python
# Combine dense (OpenAI) + sparse (BM25 keyword)
# Best of both worlds
```
**Pros**: Captures semantic + exact keyword matches
**Cons**: Complex setup, need both systems
**Best for**: Production systems, maximum recall

---

### **3. Vector Database Options**

#### **Option 3A: ChromaDB** ⭐⭐ *Recommended*
```python
# Local, persistent, simple API
client = chromadb.PersistentClient(path="./chroma_db")
```
**Pros**: Easy setup, good performance, LangChain integration
**Cons**: Not for massive scale (10M+ vectors)
**Best for**: Development, small-medium datasets

#### **Option 3B: FAISS** ⭐⭐⭐ *High Performance*
```python
# Facebook's similarity search library
# Ultra-fast, optimized for billions of vectors
```
**Pros**: Fastest search, mature, production-tested
**Cons**: No server mode, harder to use, RAM-intensive
**Best for**: Large datasets, latency-critical apps

#### **Option 3C: Pinecone/Weaviate** ⭐⭐⭐ *Cloud*
```python
# Managed vector database services
```
**Pros**: Scalable, managed, advanced features
**Cons**: Costs money, vendor lock-in
**Best for**: Production at scale, teams

#### **Option 3D: PostgreSQL + pgvector** ⭐ *Integrated*
```python
# Add vector search to existing PostgreSQL
```
**Pros**: Single database, SQL + vectors together
**Cons**: Slower than specialized DBs, limited features
**Best for**: Existing Postgres apps, simple use cases

---

### **4. RAG Patterns**

#### **Pattern 4A: Naive RAG** ⭐ *Baseline*
```
Question → Embed → Vector Search → Stuff into Prompt → LLM
```
**Pros**: Simple, works well for basic cases
**Cons**: No reranking, limited context window
**Implementation**: 30 minutes
**Quality**: 70-80% good answers

#### **Pattern 4B: RAG with Metadata Filtering** ⭐⭐ *Improved*
```
Question → Extract Filters → Filtered Vector Search → LLM
Example: "jobs last week" → filter by date_range
```
**Pros**: More relevant results, faster search
**Cons**: Requires metadata extraction
**Implementation**: 1-2 hours
**Quality**: 80-85% good answers

#### **Pattern 4C: Hybrid Search RAG** ⭐⭐⭐ *Advanced*
```
Question → Vector Search + Keyword Search → Merge → Rerank → LLM
```
**Pros**: Catches both semantic + exact matches
**Cons**: More complex, need two search systems
**Implementation**: 3-4 hours
**Quality**: 85-90% good answers

#### **Pattern 4D: Multi-Query RAG** ⭐⭐⭐ *Robust*
```
Question → Generate Multiple Query Variations → 
Search Each → Combine Results → Rerank → LLM
```
**Pros**: Handles ambiguous questions better
**Cons**: Multiple LLM calls, slower
**Implementation**: 2-3 hours
**Quality**: 90-95% good answers

#### **Pattern 4E: Agentic RAG** ⭐⭐⭐⭐ *Cutting Edge*
```
Question → Agent Plans Retrieval Strategy → 
Iterative Retrieval + Reasoning → Self-Reflection → Answer
```
**Pros**: Can handle complex multi-hop questions
**Cons**: Most complex, higher costs, slower
**Implementation**: 4-6 hours
**Quality**: 95%+ good answers

---

## 🎓 Recommended Learning Path

### **For Your FSIA Use Case:**

I recommend **Path A (Fundamentals) + Selected Advanced Features**

**Reasoning**:
1. You have good data volume (370 text entries) to learn from
2. Clear use cases (work logs, receipts, rules)
3. Can demonstrate concepts without over-engineering
4. Build foundation, then layer complexity

### **Proposed Implementation:**

#### **Step 1: Basic Chunking (30 min)**
- Implement recursive character splitting
- Experiment with chunk sizes (250, 500, 1000)
- Visualize chunk boundaries on sample data

#### **Step 2: Embeddings (1 hour)**
- Use OpenAI `text-embedding-3-small`
- Embed all work descriptions, receipts, rules
- Explore embedding space (similarity visualization)

#### **Step 3: Vector Store Setup (1 hour)**
- ChromaDB with persistent storage
- Create collections for each data type
- Test basic similarity search

#### **Step 4: Naive RAG (1 hour)**
- Simple retrieve → stuff → answer flow
- Test questions like:
  - "What work was done on HVAC installations?"
  - "Show me receipts for electrical materials"
  - "What are the overtime rules?"

#### **Step 5: Evaluation & Optimization (2 hours)**
- Create test questions with expected answers
- Measure retrieval quality (precision, recall)
- Experiment with:
  - Different chunk sizes
  - Number of chunks retrieved (k=3 vs k=5)
  - Similarity thresholds

#### **Step 6: Add One Advanced Feature (2 hours)**
Pick ONE to go deeper:

**Option A: Metadata Filtering**
```python
# Filter by date, technician, job_id before vector search
results = collection.query(
    query_embeddings=[question_embedding],
    where={"date": {"$gte": "2026-01-01"}},
    n_results=5
)
```

**Option B: Hybrid Search**
```python
# Combine dense vectors + BM25 keyword search
# Use Reciprocal Rank Fusion to merge results
```

**Option C: Reranking**
```python
# Use cross-encoder to rerank retrieved chunks
# Better relevance than pure vector similarity
```

---

## 📊 Use Cases for FSIA RAG System

### **High-Value Questions RAG Can Answer:**

1. **Work Pattern Discovery**
   - "Show me all jobs where technicians mentioned customer complaints"
   - "What are common issues in HVAC repairs based on work logs?"
   - "Find work logs mentioning emergency or urgent situations"

2. **Expense Intelligence**
   - "What materials were purchased for electrical work?"
   - "Show me receipts from hardware stores"
   - "Find expenses that mention specific vendors"

3. **Policy & Rule Lookup**
   - "What are the rules about overtime?"
   - "How should we handle weekend work?"
   - "What's the policy on travel reimbursement?"

4. **Hybrid SQL + Vector Queries** (Phase 4 preview)
   - "Show me expensive jobs where work logs mention delays"
   - SQL finds expensive jobs → Vector finds delay mentions
   - Combines structured + unstructured data

---

## 🔬 Experiments to Try

### **Chunking Experiments:**
1. Compare chunk sizes: 250 vs 500 vs 1000 characters
2. Test overlap: 0 vs 50 vs 100 characters
3. Try semantic chunking on sample work logs

### **Embedding Experiments:**
1. Compare OpenAI vs Sentence Transformers quality
2. Measure embedding latency and cost
3. Test dimension reduction (3072 → 1536 → 768)

### **Retrieval Experiments:**
1. Vary k (number of chunks): 3 vs 5 vs 10
2. Test similarity thresholds: 0.6 vs 0.7 vs 0.8
3. Compare MMR (diversity) vs pure similarity

### **RAG Experiments:**
1. Naive RAG vs RAG with context compression
2. Single query vs multi-query variations
3. Measure answer quality with/without reranking

---

## 📈 Success Metrics

Track these to measure progress:

1. **Retrieval Metrics**:
   - **Precision**: % of retrieved chunks that are relevant
   - **Recall**: % of relevant chunks that were retrieved
   - **MRR**: Mean Reciprocal Rank (rank of first relevant result)

2. **Quality Metrics**:
   - **Answer Accuracy**: % of correct answers (manual evaluation)
   - **Hallucination Rate**: % of answers with made-up facts
   - **Source Attribution**: Can trace answer to source chunk?

3. **Performance Metrics**:
   - **Latency**: Time from question to answer
   - **Cost**: Embedding + LLM costs per query
   - **Cache Hit Rate**: % of queries using cached embeddings

---

## 🛠️ Technical Implementation Options

### **Minimal Setup (1-2 hours)**
```python
# Quick start to see RAG in action
Tools:
- LangChain RecursiveCharacterTextSplitter
- OpenAI text-embedding-3-small
- ChromaDB (in-memory)
- LangChain RetrievalQA

Result: Working RAG pipeline, basic understanding
```

### **Recommended Setup (4-6 hours)**
```python
# Solid foundation for learning and experimentation
Tools:
- Custom chunking with metadata
- OpenAI embeddings with caching
- ChromaDB (persistent)
- Custom RAG chain with logging
- Evaluation suite

Result: Production-ready RAG, deep understanding
```

### **Advanced Setup (8-10 hours)**
```python
# Explore multiple approaches, choose best
Tools:
- Multiple chunking strategies (A/B test)
- Hybrid embeddings (dense + sparse)
- ChromaDB with advanced indexing
- Reranking with cross-encoders
- Multi-query + fusion
- Comprehensive eval framework

Result: Optimized RAG system, expert knowledge
```

---

## 📝 Deliverables for Phase 3

### **Code Artifacts:**
1. `src/utils/chunking.py` - Chunking strategies (updated with new methods)
2. `src/services/embedding_service.py` - Embedding generation + caching
3. `src/services/vector_store.py` - ChromaDB wrapper with collections
4. `src/agents/rag_agent.py` - RAG query pipeline
5. `test_phase3_rag.py` - Demo script with experiments
6. `docs/PHASE3_EXPERIMENTS.md` - Results from experiments

### **Documentation:**
1. Chunking strategy comparison (with examples)
2. Embedding model benchmarks (quality + cost)
3. RAG evaluation results (test questions + scores)
4. Lessons learned and recommendations

### **Demo Capabilities:**
```bash
# Run Phase 3 demo
npm run backend:phase3

# Ask questions like:
"Show me work logs about HVAC repairs"
"What expenses mention electrical materials?"
"Explain the overtime policy"
"Find jobs where technicians mentioned delays"
```

---

## 🤔 Decision Points: What Would You Like?

I need your input on:

### **1. Learning Depth**
- [ ] **Quick Overview** (Path A - Minimal, 1-2 hours)
- [ ] **Solid Foundation** (Path A - Recommended, 4-6 hours) ⭐
- [ ] **Deep Dive** (Path B - Production, 8-10 hours)
- [ ] **Comparison Study** (Path C - Experimentation, 6-8 hours)

### **2. Chunking Strategy**
- [ ] Start simple (recursive character) ⭐
- [ ] Jump to semantic chunking
- [ ] Compare multiple approaches

### **3. Embedding Model**
- [ ] OpenAI only (simple, costs money) ⭐
- [ ] Sentence Transformers only (free, local)
- [ ] Try both and compare

### **4. RAG Pattern**
- [ ] Naive RAG first, iterate later ⭐
- [ ] Start with hybrid search
- [ ] Build multi-query from start

### **5. Special Focus**
What interests you most? (Pick 1-2)
- [ ] Chunking strategies (how size affects quality)
- [ ] Embedding space visualization (see vectors)
- [ ] Retrieval optimization (precision/recall trade-offs)
- [ ] Reranking techniques (cross-encoders)
- [ ] Hybrid search (vector + keyword)
- [ ] Production patterns (caching, monitoring)

---

## 🚀 Next Steps

**Once you choose your path, I will:**

1. Create detailed implementation plan for your chosen approach
2. Build code with extensive comments explaining concepts
3. Add experiments to demonstrate trade-offs
4. Create visualization tools to "see" embeddings and retrieval
5. Build evaluation framework to measure quality

**Let me know:**
- Which path appeals to you? (A, B, or C)
- Any specific topics you want to emphasize?
- Timeline constraints?

Then we'll build an amazing RAG system together! 🎉
