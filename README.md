# LayaPulse

> **"Understand the live conversation."**

Real-time X/Twitter intelligence dashboard powered by the Laya decision engine, streaming data, vector search, and RAG.

## Quick Start

### 1. Start the Backend

```bash
cd backend
python main.py
```

The API server starts at **http://localhost:8000**

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

The dashboard opens at **http://localhost:3000**

### 3. Demo

Open http://localhost:3000 — mock posts will stream in automatically.

- Watch live posts arrive with Laya classification
- See sentiment, topics, and trending entities update
- Click "Why this classification?" on any post for explainability
- Ask questions in the RAG panel (e.g., "What happened in AI today?")
- Create alerts in the Alerts tab
- Search and filter in the Search tab

## Architecture

```
X/Twitter API or Mock Feed
  → Streaming ingestion
  → Event queue (asyncio)
  → Post Processing Pipeline (3 workers)
    → Laya Classification
    → Embedding Generation
    → Database Storage (SQLite)
    → Vector Store Indexing (in-memory)
    → Event Detection
    → Alert Checking
  → WebSocket broadcast
  → Real-time Dashboard (Next.js)
```

## Provider Interfaces

All AI components are behind swappable interfaces:

| Interface | Mock | Production |
|-----------|------|------------|
| `StreamProvider` | MockStreamProvider | TwitterStreamProvider |
| `LayaClassifier` | MockLayaClassifier | LayaClassifier (real model) |
| `EmbeddingProvider` | MockEmbeddingProvider | OpenAIEmbeddingProvider |
| `VectorStore` | MockVectorStore | QdrantStore / PgVectorStore |
| `LLMProvider` | MockLLMProvider | OpenAIProvider / GeminiProvider |

## Configuration

All settings via environment variables in `backend/.env`:

- `STREAM_MODE` — `mock` or `twitter`
- `LLM_PROVIDER` — `mock`, `openai`, or `gemini`
- `EMBEDDING_PROVIDER` — `mock` or `openai`
- `VECTOR_STORE_TYPE` — `memory`, `qdrant`, or `pgvector`

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, asyncio
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Recharts
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Vector Store**: In-memory (dev) / Qdrant or pgvector (prod)
- **Real-time**: WebSocket
