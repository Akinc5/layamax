"""
LayaPulse — FastAPI application entry point.

Wires together providers, pipeline, services, and API routes.
Starts the stream ingestion + processing pipeline on startup.
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from mock_providers import (
    MockEmbeddingProvider,
    MockLayaClassifier,
    MockLLMProvider,
    MockStreamProvider,
    MockVectorStore,
)
from pipeline import PostProcessingPipeline
from providers import EmbeddingProvider, LayaClassifier, LLMProvider, StreamProvider, VectorStore
from schemas import (
    CreateAlertRequest,
    PostResponse,
    RAGRequest,
    RAGResponse,
    SearchRequest,
)
from services import (
    AlertsService,
    AnalyticsService,
    EventsService,
    PostsService,
    RAGService,
    SearchService,
)
from ws_manager import ws_manager

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("layapulse")

# ── Provider registry ──────────────────────────────────────────────────
classifier: LayaClassifier
embedder: EmbeddingProvider
vector_store: VectorStore
llm: LLMProvider
stream: StreamProvider
pipeline: PostProcessingPipeline

# ── Services ───────────────────────────────────────────────────────────
analytics_svc = AnalyticsService()
events_svc = EventsService()
search_svc = SearchService()
alerts_svc = AlertsService()
posts_svc = PostsService()
rag_svc: RAGService


# ═══════════════════════════════════════════════════════════════════════════
#  LIFESPAN — startup / shutdown
# ═══════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    global classifier, embedder, vector_store, llm, stream, pipeline, rag_svc

    # 1. Initialise database
    logger.info("Initialising database …")
    await init_db()

    # 2. Create providers (swap implementations here)
    logger.info("Creating providers (mode=%s, llm=%s) …", settings.stream_mode, settings.llm_provider)
    classifier = MockLayaClassifier()

    # Embedding provider
    if settings.embedding_provider == "openai" and settings.openai_api_key:
        from real_providers import OpenAIEmbeddingProvider
        embedder = OpenAIEmbeddingProvider()
    else:
        embedder = MockEmbeddingProvider(dim=settings.embedding_dim)

    vector_store = MockVectorStore()

    # LLM provider
    if settings.llm_provider == "openai" and settings.openai_api_key:
        from real_providers import OpenAILLMProvider
        llm = OpenAILLMProvider()
    elif settings.llm_provider == "gemini" and settings.gemini_api_key:
        from real_providers import GeminiLLMProvider
        llm = GeminiLLMProvider()
    else:
        llm = MockLLMProvider()

    # Stream provider
    if settings.stream_mode == "twitter":
        from twitter_provider import TwitterStreamProvider
        stream = TwitterStreamProvider(
            bearer_token=settings.twitter_bearer_token,
            search_query=settings.twitter_search_query,
            stream_type=settings.twitter_stream_type,
            poll_interval=settings.twitter_poll_interval,
        )
    else:
        stream = MockStreamProvider(interval=settings.mock_post_interval)

    # 3. RAG service
    rag_svc = RAGService(embedder, vector_store, llm)

    # 4. Start pipeline
    pipeline = PostProcessingPipeline(classifier, embedder, vector_store)
    await pipeline.start(num_workers=3)

    # 5. Start stream ingestion
    ingest_task = asyncio.create_task(_ingest_stream(stream, pipeline))

    logger.info("✅  LayaPulse is live!")

    yield  # ← app is running

    # Shutdown
    logger.info("Shutting down …")
    await stream.stop()
    ingest_task.cancel()
    await pipeline.stop()


async def _ingest_stream(stream: StreamProvider, pipeline: PostProcessingPipeline):
    """Read from the stream and push posts into the pipeline queue."""
    try:
        async for post in stream.stream():
            await pipeline.enqueue(post)
    except asyncio.CancelledError:
        pass


# ═══════════════════════════════════════════════════════════════════════════
#  FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="LayaPulse",
    description="Real-Time X/Twitter Intelligence powered by Laya",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET
# ═══════════════════════════════════════════════════════════════════════════
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep the connection alive; client can send pings
            data = await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)


# ═══════════════════════════════════════════════════════════════════════════
#  REST API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

# ── Dashboard stats ────────────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    return pipeline.stats.to_dashboard().model_dump(mode="json")


# ── Posts ──────────────────────────────────────────────────────────────
@app.get("/api/posts", response_model=List[PostResponse])
async def get_posts(limit: int = Query(50, le=200)):
    return await posts_svc.get_recent(limit)


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int):
    post = await posts_svc.get_post(post_id)
    if not post:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# ── Topics ────────────────────────────────────────────────────────────
@app.get("/api/topics/{topic}/posts", response_model=List[PostResponse])
async def get_topic_posts(topic: str, limit: int = Query(50, le=200)):
    return await posts_svc.get_by_topic(topic, limit)


@app.get("/api/categories")
async def get_categories():
    return await classifier.get_categories()


@app.put("/api/categories")
async def update_categories(categories: List[str]):
    await classifier.set_categories(categories)
    return {"status": "ok", "categories": categories}


# ── Analytics ─────────────────────────────────────────────────────────
@app.get("/api/analytics")
async def get_analytics(hours: float = Query(24, ge=0.1, le=168)):
    return await analytics_svc.get_analytics(hours)


# ── Events ────────────────────────────────────────────────────────────
@app.get("/api/events")
async def get_events(status: str = "active", limit: int = Query(20, le=100)):
    return await events_svc.get_events(status, limit)


@app.get("/api/events/{event_id}/posts", response_model=List[PostResponse])
async def get_event_posts(event_id: int):
    return await events_svc.get_event_posts(event_id)


# ── RAG ───────────────────────────────────────────────────────────────
@app.post("/api/rag", response_model=RAGResponse)
async def rag_query(req: RAGRequest):
    return await rag_svc.query(req.question, req.time_range_hours)


@app.post("/api/rag/stream")
async def rag_query_stream(req: RAGRequest):
    """Server-Sent Events endpoint streaming live RAG responses and citations."""
    async def event_generator():
        async for chunk in rag_svc.query_stream(req.question, req.time_range_hours):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ── Stream Management & Live Ingestion ────────────────────────────────
@app.get("/api/stream/status")
async def get_stream_status():
    """Returns the live stream configuration and status."""
    return {
        "stream_mode": settings.stream_mode,
        "is_configured": bool(settings.twitter_bearer_token and len(settings.twitter_bearer_token) > 10),
        "search_query": settings.twitter_search_query,
        "stream_type": settings.twitter_stream_type,
        "poll_interval": settings.twitter_poll_interval,
        "posts_received": pipeline.stats.posts_received,
        "posts_analyzed": pipeline.stats.posts_analyzed,
    }


@app.post("/api/stream/ingest")
async def ingest_custom_tweet(text: str = Query(..., description="Tweet text to classify live"), author: str = Query("custom_user")):
    """Injects any live tweet or text immediately into the live processing pipeline."""
    from datetime import datetime
    import uuid
    raw = RawPost(
        external_id=f"manual_{uuid.uuid4().hex[:10]}",
        author_name=author,
        author_username=author,
        author_avatar=f"https://api.dicebear.com/7.x/initials/svg?seed={author}",
        text=text,
        timestamp=datetime.utcnow(),
        url="https://x.com",
    )
    await pipeline.enqueue(raw)
    return {"status": "enqueued", "external_id": raw.external_id}



# ── Search ────────────────────────────────────────────────────────────
@app.post("/api/search", response_model=List[PostResponse])
async def search_posts(req: SearchRequest):
    return await search_svc.search(
        keyword=req.keyword,
        username=req.username,
        hashtag=req.hashtag,
        topic=req.topic,
        sentiment=req.sentiment,
        importance=req.importance,
        min_relevance=req.min_relevance,
        start_date=req.start_date,
        end_date=req.end_date,
        limit=req.limit,
        offset=req.offset,
    )


# ── Alerts ────────────────────────────────────────────────────────────
@app.get("/api/alerts")
async def list_alerts():
    return await alerts_svc.list_alerts()


@app.post("/api/alerts")
async def create_alert(req: CreateAlertRequest):
    alert_id = await alerts_svc.create_alert(req.name, req.conditions)
    return {"id": alert_id, "status": "created"}


@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    ok = await alerts_svc.delete_alert(alert_id)
    return {"deleted": ok}


@app.get("/api/alerts/notifications")
async def get_notifications(limit: int = 50, unread_only: bool = False):
    return await alerts_svc.get_notifications(limit, unread_only)


@app.put("/api/alerts/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int):
    await alerts_svc.mark_read(notification_id)
    return {"status": "ok"}


# ── Evaluation Benchmarks ──────────────────────────────────────────────
@app.get("/api/eval/metrics")
async def get_eval_metrics():
    """Returns the latest evaluation benchmark results from disk."""
    import json
    import os
    eval_file = os.path.join(os.path.dirname(__file__), "eval_results.json")
    if os.path.exists(eval_file):
        with open(eval_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "not_run_yet", "message": "Run python run_eval.py to execute the evaluation harness"}


@app.post("/api/eval/run")
async def trigger_eval_run():
    """Triggers an on-demand evaluation suite run."""
    from eval_harness import EvaluationHarness
    harness = EvaluationHarness()
    results = await harness.run_full_suite()
    import json
    import os
    eval_file = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results


# ── Health ────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    vec_count = await vector_store.count()
    return {
        "status": "healthy",
        "stream_mode": settings.stream_mode,
        "vector_count": vec_count,
        "ws_connections": ws_manager.active_count,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
