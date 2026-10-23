"""
Post processing pipeline.

Incoming post → normalise → extract features → classify (Laya) →
embed → store in DB + vector store → detect events → check alerts →
broadcast via WebSocket.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Deque, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import (
    Alert, AlertNotification, Classification, EmbeddingRecord, Entity,
    Event, EventPost, ExtractedUrl, Hashtag, MentionedUser, Post, async_session,
)
from providers import EmbeddingProvider, LayaClassifier, StreamProvider, VectorStore
from schemas import ClassificationResult, DashboardStats, PostResponse, RawPost, EntityInfo
from ws_manager import ws_manager

logger = logging.getLogger("layapulse.pipeline")


class PipelineStats:
    """Thread‑safe rolling statistics for the processing pipeline."""

    def __init__(self) -> None:
        self.posts_received: int = 0
        self.posts_analyzed: int = 0
        self.posts_indexed: int = 0
        self.alerts_generated: int = 0
        self._latencies: Deque[float] = deque(maxlen=100)
        self._timestamps: Deque[float] = deque(maxlen=300)

    def record_post(self) -> None:
        self.posts_received += 1
        self._timestamps.append(time.time())

    def record_latency(self, ms: float) -> None:
        self._latencies.append(ms)

    @property
    def avg_latency_ms(self) -> float:
        return sum(self._latencies) / len(self._latencies) if self._latencies else 0

    @property
    def posts_per_minute(self) -> float:
        if len(self._timestamps) < 2:
            return 0
        now = time.time()
        recent = [t for t in self._timestamps if now - t < 60]
        return len(recent)

    def to_dashboard(self) -> DashboardStats:
        return DashboardStats(
            posts_received=self.posts_received,
            posts_analyzed=self.posts_analyzed,
            posts_indexed=self.posts_indexed,
            alerts_generated=self.alerts_generated,
            posts_per_minute=round(self.posts_per_minute, 1),
            avg_latency_ms=round(self.avg_latency_ms, 1),
            is_live=True,
            stream_mode=settings.stream_mode,
        )


class PostProcessingPipeline:
    """
    The main intelligence pipeline.

    Orchestrates:
    1. Text normalisation + feature extraction
    2. Laya classification
    3. Embedding generation
    4. Database persistence
    5. Vector store indexing
    6. Event detection
    7. Alert checking
    8. WebSocket broadcasting
    """

    def __init__(
        self,
        classifier: LayaClassifier,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.classifier = classifier
        self.embedder = embedder
        self.vector_store = vector_store
        self.stats = PipelineStats()
        self._queue: asyncio.Queue[RawPost] = asyncio.Queue(maxsize=500)
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._db_lock = asyncio.Lock()

    # ── Public API ──────────────────────────────────────────────────────
    async def enqueue(self, post: RawPost) -> None:
        """Add a post to the processing queue (non‑blocking)."""
        self.stats.record_post()
        try:
            self._queue.put_nowait(post)
        except asyncio.QueueFull:
            logger.warning("Pipeline queue full — dropping post %s", post.external_id)

    async def start(self, num_workers: int = 3) -> None:
        """Start background processing workers."""
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("Pipeline started with %d workers", num_workers)

    async def stop(self) -> None:
        self._running = False
        for t in self._workers:
            t.cancel()
        self._workers.clear()
        logger.info("Pipeline stopped")

    # ── Worker ──────────────────────────────────────────────────────────
    async def _worker(self, worker_id: int) -> None:
        logger.info("Worker %d started", worker_id)
        while self._running:
            try:
                post = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                await self._process(post)
            except Exception:
                logger.exception("Error processing post %s", post.external_id)

    # ── Core processing ─────────────────────────────────────────────────
    async def _process(self, raw: RawPost) -> None:
        start = time.time()

        # 1. Normalise text
        text = self._normalise(raw.text)

        # 2. Extract features
        hashtags = self._extract_hashtags(text)
        urls = self._extract_urls(raw.text)
        mentions = self._extract_mentions(raw.text)

        # 3. Classify with Laya
        classification = await self.classifier.classify(text, {"author": raw.author_username})
        self.stats.posts_analyzed += 1

        # 4. Generate embedding
        embedding_id = f"emb_{uuid.uuid4().hex[:12]}"
        vector = await self.embedder.embed(text)

        # 5. Persist to database
        async with self._db_lock:
            async with async_session() as session:
                async with session.begin():
                    post = Post(
                        external_id=raw.external_id,
                        author_name=raw.author_name,
                        author_username=raw.author_username,
                        author_avatar=raw.author_avatar,
                        text=raw.text,
                        timestamp=raw.timestamp,
                        url=raw.url,
                        likes=raw.likes,
                        reposts=raw.reposts,
                        replies=raw.replies,
                        views=raw.views,
                        processing_timestamp=datetime.utcnow(),
                    )
                    session.add(post)
                    await session.flush()

                    # Classification
                    cls_record = Classification(
                        post_id=post.id,
                        category=classification.category,
                        sentiment=classification.sentiment,
                        sentiment_score=classification.sentiment_score,
                        relevance=classification.relevance,
                        importance=classification.importance,
                        importance_score=classification.importance_score,
                        should_index=classification.should_index,
                        should_alert=classification.should_alert,
                        is_significant_event=classification.is_significant_event,
                        explanation=classification.explanation,
                        raw_output=classification.raw_output,
                    )
                    session.add(cls_record)

                    # Hashtags
                    for tag in hashtags:
                        session.add(Hashtag(tag=tag, post_id=post.id))

                    # Entities
                    for ent in classification.entities:
                        session.add(Entity(name=ent.name, entity_type=ent.entity_type, post_id=post.id))

                    # Mentions
                    for uname in mentions:
                        session.add(MentionedUser(username=uname, post_id=post.id))

                    # URLs
                    for u in urls:
                        session.add(ExtractedUrl(url=u, post_id=post.id))

                    # Embedding record
                    emb_record = EmbeddingRecord(
                        post_id=post.id,
                        embedding_id=embedding_id,
                        model_name=self.embedder.model_name,
                    )
                    session.add(emb_record)

                    post_id = post.id

        # 6. Index in vector store
        if classification.should_index:
            await self.vector_store.add(
                embedding_id,
                vector,
                {
                    "post_id": post_id,
                    "category": classification.category,
                    "importance": classification.importance,
                    "sentiment": classification.sentiment,
                    "timestamp": raw.timestamp.isoformat(),
                    "author": raw.author_username,
                    "text": raw.text[:200],
                },
            )
            self.stats.posts_indexed += 1

        # 7. Event detection
        if classification.is_significant_event:
            await self._handle_event(post_id, raw, classification)

        # 8. Alert checking
        await self._check_alerts(post_id, raw, classification)

        # Record latency
        latency_ms = (time.time() - start) * 1000
        self.stats.record_latency(latency_ms)

        # 9. Broadcast via WebSocket
        post_response = PostResponse(
            id=post_id,
            external_id=raw.external_id,
            author_name=raw.author_name,
            author_username=raw.author_username,
            author_avatar=raw.author_avatar,
            text=raw.text,
            timestamp=raw.timestamp,
            url=raw.url,
            likes=raw.likes,
            reposts=raw.reposts,
            replies=raw.replies,
            views=raw.views,
            processing_timestamp=datetime.utcnow(),
            category=classification.category,
            sentiment=classification.sentiment,
            sentiment_score=classification.sentiment_score,
            relevance=classification.relevance,
            importance=classification.importance,
            importance_score=classification.importance_score,
            should_index=classification.should_index,
            should_alert=classification.should_alert,
            is_significant_event=classification.is_significant_event,
            explanation=classification.explanation,
            hashtags=hashtags,
            entities=[EntityInfo(name=e.name, entity_type=e.entity_type) for e in classification.entities],
            mentioned_users=mentions,
            extracted_urls=urls,
        )

        await ws_manager.broadcast({
            "type": "new_post",
            "data": post_response.model_dump(mode="json"),
        })
        await ws_manager.broadcast({
            "type": "stats_update",
            "data": self.stats.to_dashboard().model_dump(mode="json"),
        })

    # ── Event handling ──────────────────────────────────────────────────
    async def _handle_event(
        self, post_id: int, raw: RawPost, cls: ClassificationResult
    ) -> None:
        entity_names = [e.name for e in cls.entities]
        title = self._generate_event_title(raw.text, cls)

        async with async_session() as session:
            async with session.begin():
                # Check if there's a recent similar event
                cutoff = datetime.utcnow() - timedelta(hours=1)
                result = await session.execute(
                    select(Event).where(
                        Event.category == cls.category,
                        Event.status == "active",
                        Event.first_detected >= cutoff,
                    )
                )
                existing = result.scalars().first()

                if existing:
                    existing.post_count += 1
                    existing.last_updated = datetime.utcnow()
                    event_id = existing.id
                else:
                    event = Event(
                        title=title,
                        description=raw.text[:300],
                        category=cls.category,
                        severity=cls.importance,
                        first_detected=datetime.utcnow(),
                        last_updated=datetime.utcnow(),
                        post_count=1,
                        related_entities=entity_names,
                    )
                    session.add(event)
                    await session.flush()
                    event_id = event.id

                session.add(EventPost(event_id=event_id, post_id=post_id))

        # Broadcast event
        await ws_manager.broadcast({
            "type": "new_event",
            "data": {
                "id": event_id,
                "title": title,
                "category": cls.category,
                "severity": cls.importance,
                "related_entities": entity_names,
                "post_count": 1,
            },
        })

    def _generate_event_title(self, text: str, cls: ClassificationResult) -> str:
        """Generate a concise event title from the post text."""
        # Use first sentence or first 80 chars
        sentences = re.split(r'[.!?]', text)
        title = sentences[0].strip() if sentences else text[:80]
        # Remove emojis and hashtags for cleaner title
        title = re.sub(r'[#@]\w+', '', title).strip()
        title = re.sub(r'[^\w\s\-:,]', '', title).strip()
        if len(title) > 100:
            title = title[:97] + "..."
        return title or f"New {cls.category} Event"

    # ── Alert checking ──────────────────────────────────────────────────
    async def _check_alerts(
        self, post_id: int, raw: RawPost, cls: ClassificationResult
    ) -> None:
        async with async_session() as session:
            result = await session.execute(select(Alert).where(Alert.active == True))
            alerts = result.scalars().all()

        for alert in alerts:
            if self._matches_alert(alert.conditions, raw, cls):
                async with async_session() as session:
                    async with session.begin():
                        notif = AlertNotification(
                            alert_id=alert.id,
                            post_id=post_id,
                            message=f"Alert '{alert.name}' triggered by @{raw.author_username}: {raw.text[:100]}",
                        )
                        session.add(notif)

                self.stats.alerts_generated += 1
                await ws_manager.broadcast({
                    "type": "new_alert",
                    "data": {
                        "alert_name": alert.name,
                        "post_id": post_id,
                        "message": f"@{raw.author_username}: {raw.text[:100]}",
                    },
                })

    def _matches_alert(
        self, conditions: Dict[str, Any], raw: RawPost, cls: ClassificationResult
    ) -> bool:
        """Check if a post matches alert conditions."""
        for key, value in conditions.items():
            if key == "topic" and cls.category.lower() != str(value).lower():
                return False
            if key == "keyword" and str(value).lower() not in raw.text.lower():
                return False
            if key == "username" and raw.author_username.lower() != str(value).lower():
                return False
            if key == "hashtag":
                ht = str(value).lower().lstrip("#")
                if ht not in raw.text.lower():
                    return False
            if key == "importance":
                levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                if levels.get(cls.importance, 0) < levels.get(str(value), 0):
                    return False
            if key == "min_relevance" and cls.relevance < float(value):
                return False
            if key == "sentiment" and cls.sentiment != str(value):
                return False
        return True

    # ── Text utilities ──────────────────────────────────────────────────
    @staticmethod
    def _normalise(text: str) -> str:
        # Collapse whitespace, strip
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _extract_hashtags(text: str) -> List[str]:
        return re.findall(r'#(\w+)', text)

    @staticmethod
    def _extract_urls(text: str) -> List[str]:
        return re.findall(r'https?://[^\s]+', text)

    @staticmethod
    def _extract_mentions(text: str) -> List[str]:
        return re.findall(r'@(\w+)', text)
