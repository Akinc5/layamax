"""
Business‑logic services: analytics, RAG, events, alerts, search.
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import (
    Alert, AlertNotification, Classification, Entity, Event, EventPost,
    ExtractedUrl, Hashtag, MentionedUser, Post, async_session,
)
from providers import EmbeddingProvider, LLMProvider, VectorStore
from schemas import (
    ActivityPoint, AnalyticsResponse, EntityInfo, EventResponse,
    ImportanceBreakdown, PostResponse, RAGCitation, RAGResponse,
    SentimentBreakdown, TopicCount, TrendingEntity,
)


# ═══════════════════════════════════════════════════════════════════════════
#  ANALYTICS SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class AnalyticsService:
    """Computes real‑time analytics from stored posts + classifications."""

    async def get_analytics(self, hours: float = 24) -> AnalyticsResponse:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        async with async_session() as session:
            # Sentiment breakdown
            result = await session.execute(
                select(Classification.sentiment, func.count(Classification.id))
                .join(Post, Classification.post_id == Post.id)
                .where(Post.timestamp >= cutoff)
                .group_by(Classification.sentiment)
            )
            sentiment_counts = {row[0]: row[1] for row in result.all()}

            # Topic breakdown
            result = await session.execute(
                select(Classification.category, func.count(Classification.id))
                .join(Post, Classification.post_id == Post.id)
                .where(Post.timestamp >= cutoff)
                .group_by(Classification.category)
                .order_by(func.count(Classification.id).desc())
                .limit(12)
            )
            topics = [TopicCount(topic=row[0], count=row[1]) for row in result.all()]

            # Activity timeline (posts per 10‑min bucket)
            result = await session.execute(
                select(Post.timestamp).where(Post.timestamp >= cutoff).order_by(Post.timestamp)
            )
            timestamps = [row[0] for row in result.all()]

            # Build 10-minute buckets
            activity: List[ActivityPoint] = []
            if timestamps:
                bucket_size = timedelta(minutes=10)
                bucket_start = cutoff
                while bucket_start < datetime.utcnow():
                    bucket_end = bucket_start + bucket_size
                    count = sum(1 for t in timestamps if bucket_start <= t < bucket_end)
                    activity.append(ActivityPoint(
                        timestamp=bucket_start.strftime("%H:%M"),
                        count=count,
                    ))
                    bucket_start = bucket_end

            # Importance breakdown
            result = await session.execute(
                select(Classification.importance, func.count(Classification.id))
                .join(Post, Classification.post_id == Post.id)
                .where(Post.timestamp >= cutoff)
                .group_by(Classification.importance)
            )
            imp_counts = {row[0]: row[1] for row in result.all()}

            # Trending entities (with velocity calculation)
            # Compare last 30 min vs previous 30 min
            now = datetime.utcnow()
            recent_cutoff = now - timedelta(minutes=30)
            old_cutoff = now - timedelta(minutes=60)

            result = await session.execute(
                select(Entity.name, func.count(Entity.id))
                .join(Post, Entity.post_id == Post.id)
                .where(Post.timestamp >= recent_cutoff)
                .group_by(Entity.name)
                .order_by(func.count(Entity.id).desc())
                .limit(20)
            )
            recent_entities = {row[0]: row[1] for row in result.all()}

            result = await session.execute(
                select(Entity.name, func.count(Entity.id))
                .join(Post, Entity.post_id == Post.id)
                .where(and_(Post.timestamp >= old_cutoff, Post.timestamp < recent_cutoff))
                .group_by(Entity.name)
            )
            old_entities = {row[0]: row[1] for row in result.all()}

            trending: List[TrendingEntity] = []
            for name, count in recent_entities.items():
                old_count = old_entities.get(name, 0)
                velocity = (count - old_count) / 30.0  # per minute
                trend = "rising" if velocity > 0.05 else ("falling" if velocity < -0.05 else "stable")
                trending.append(TrendingEntity(
                    name=name, count=count, velocity=round(velocity, 3), trend=trend,
                ))
            trending.sort(key=lambda x: x.velocity, reverse=True)

        return AnalyticsResponse(
            sentiment=SentimentBreakdown(
                positive=sentiment_counts.get("positive", 0),
                neutral=sentiment_counts.get("neutral", 0),
                negative=sentiment_counts.get("negative", 0),
            ),
            topics=topics,
            activity=activity[-30:],  # last 30 buckets
            importance=ImportanceBreakdown(
                low=imp_counts.get("LOW", 0),
                medium=imp_counts.get("MEDIUM", 0),
                high=imp_counts.get("HIGH", 0),
                critical=imp_counts.get("CRITICAL", 0),
            ),
            trending_entities=trending[:10],
        )


# ═══════════════════════════════════════════════════════════════════════════
#  RAG SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class RAGService:
    """
    Retrieval‑Augmented Generation over indexed posts.

    Combines semantic similarity with recency weighting.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
        llm: LLMProvider,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm = llm

    async def query(self, question: str, time_range_hours: Optional[float] = None) -> RAGResponse:
        start = time.time()

        # 1. Embed the question
        q_vector = await self.embedder.embed(question)

        # 2. Build metadata filter for time range
        filter_meta = None
        if time_range_hours:
            cutoff = datetime.utcnow() - timedelta(hours=time_range_hours)
            filter_meta = {"min_timestamp": cutoff.isoformat()}

        # 3. Semantic search
        results = await self.vector_store.search(q_vector, top_k=15, filter_metadata=filter_meta)

        if not results:
            return RAGResponse(
                answer="I don't have enough relevant posts in the current feed to answer this question. Try a broader query or wait for more data.",
                citations=[],
                query_time_ms=round((time.time() - start) * 1000, 1),
            )

        # 4. Apply recency weighting
        now = datetime.utcnow()
        scored_results = []
        for eid, sim_score, meta in results:
            try:
                ts = datetime.fromisoformat(meta.get("timestamp", ""))
                age_hours = max(0.1, (now - ts).total_seconds() / 3600)
                recency_boost = 1.0 / (1.0 + age_hours * 0.1)
            except (ValueError, TypeError):
                recency_boost = 0.5
            final_score = sim_score * 0.7 + recency_boost * 0.3
            scored_results.append((eid, final_score, meta))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_results[:8]

        # 5. Build context
        context_parts = []
        citations = []
        for eid, score, meta in top_results:
            post_id = meta.get("post_id", 0)
            text = meta.get("text", "")
            author = meta.get("author", "unknown")
            timestamp = meta.get("timestamp", "")

            context_parts.append(
                f"Author: @{author}\n"
                f"Text: {text}\n"
                f"Category: {meta.get('category', 'N/A')}\n"
                f"Timestamp: {timestamp}\n"
                f"Importance: {meta.get('importance', 'N/A')}"
            )

            try:
                ts = datetime.fromisoformat(timestamp)
            except (ValueError, TypeError):
                ts = now

            citations.append(RAGCitation(
                post_id=post_id,
                author_username=author,
                text=text,
                timestamp=ts,
                relevance_score=round(score * 100, 1),
            ))

        context = "\n---\n".join(context_parts)

        # 6. Generate answer
        system_prompt = (
            "You are LayaPulse, a real-time social media intelligence analyst. "
            "Answer the user's question using ONLY the provided post context. "
            "Never invent information not present in the sources. "
            "Include specific details from the posts. "
            "Cite sources by mentioning the author's username."
        )
        answer = await self.llm.generate(
            prompt=question,
            context=context,
            system_prompt=system_prompt,
        )

        return RAGResponse(
            answer=answer,
            citations=citations,
            query_time_ms=round((time.time() - start) * 1000, 1),
        )

    async def query_stream(
        self, question: str, time_range_hours: Optional[float] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Streaming version of RAG query yielding citations first, then tokens in real time."""
        start = time.time()

        # 1. Embed question & retrieve matching posts
        q_vector = await self.embedder.embed(question)
        filter_meta = None
        if time_range_hours:
            cutoff = datetime.utcnow() - timedelta(hours=time_range_hours)
            filter_meta = {"min_timestamp": cutoff.isoformat()}

        results = await self.vector_store.search(q_vector, top_k=15, filter_metadata=filter_meta)
        if not results:
            yield {
                "type": "citations",
                "citations": [],
                "query_time_ms": round((time.time() - start) * 1000, 1),
            }
            yield {
                "type": "token",
                "token": "I don't have enough relevant live posts in the feed yet to answer this. Try a broader search or wait for more live tweets to arrive.",
            }
            yield {"type": "done"}
            return

        # 2. Recency re-ranking
        now = datetime.utcnow()
        scored = []
        for eid, sim_score, meta in results:
            try:
                ts = datetime.fromisoformat(meta.get("timestamp", ""))
                age_hours = max(0.1, (now - ts).total_seconds() / 3600)
                recency_boost = 1.0 / (1.0 + age_hours * 0.1)
            except Exception:
                recency_boost = 0.5
            final_score = sim_score * 0.7 + recency_boost * 0.3
            scored.append((eid, final_score, meta))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_results = scored[:8]

        # 3. Context & Citations
        context_parts = []
        citations_data = []
        for eid, score, meta in top_results:
            post_id = meta.get("post_id", 0)
            text = meta.get("text", "")
            author = meta.get("author", "unknown")
            timestamp = meta.get("timestamp", "")
            context_parts.append(
                f"Author: @{author}\nText: {text}\nCategory: {meta.get('category', 'N/A')}\nTimestamp: {timestamp}"
            )
            citations_data.append({
                "post_id": post_id,
                "author_username": author,
                "text": text,
                "timestamp": timestamp,
                "relevance_score": round(score * 100, 1),
            })

        # Yield citations immediately so UI displays live sources instantly
        yield {
            "type": "citations",
            "citations": citations_data,
            "retrieval_time_ms": round((time.time() - start) * 1000, 1),
        }

        # 4. Stream LLM tokens
        context = "\n---\n".join(context_parts)
        system_prompt = (
            "You are LayaPulse, a real-time social media intelligence analyst. "
            "Answer the user's question using ONLY the provided live post context. "
            "Cite sources by mentioning author usernames."
        )

        async for token in self.llm.generate_stream(
            prompt=question, context=context, system_prompt=system_prompt
        ):
            yield {"type": "token", "token": token}

        yield {
            "type": "done",
            "total_time_ms": round((time.time() - start) * 1000, 1),
        }



# ═══════════════════════════════════════════════════════════════════════════
#  EVENTS SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class EventsService:
    """Manage detected events."""

    async def get_events(
        self, status: str = "active", limit: int = 20
    ) -> List[EventResponse]:
        async with async_session() as session:
            result = await session.execute(
                select(Event)
                .where(Event.status == status)
                .order_by(desc(Event.first_detected))
                .limit(limit)
            )
            events = result.scalars().all()
            return [
                EventResponse(
                    id=e.id,
                    title=e.title,
                    description=e.description,
                    category=e.category,
                    severity=e.severity,
                    first_detected=e.first_detected,
                    last_updated=e.last_updated,
                    post_count=e.post_count,
                    status=e.status,
                    related_entities=e.related_entities,
                )
                for e in events
            ]

    async def get_event_posts(self, event_id: int) -> List[PostResponse]:
        async with async_session() as session:
            result = await session.execute(
                select(Post)
                .join(EventPost, EventPost.post_id == Post.id)
                .where(EventPost.event_id == event_id)
                .options(
                    selectinload(Post.classification),
                    selectinload(Post.hashtags),
                    selectinload(Post.entities),
                    selectinload(Post.mentioned_users),
                )
                .order_by(desc(Post.timestamp))
            )
            posts = result.scalars().all()
            return [self._post_to_response(p) for p in posts]

    @staticmethod
    def _post_to_response(p: Post) -> PostResponse:
        cls = p.classification
        return PostResponse(
            id=p.id,
            external_id=p.external_id,
            author_name=p.author_name,
            author_username=p.author_username,
            author_avatar=p.author_avatar,
            text=p.text,
            timestamp=p.timestamp,
            url=p.url,
            likes=p.likes,
            reposts=p.reposts,
            replies=p.replies,
            views=p.views,
            processing_timestamp=p.processing_timestamp,
            category=cls.category if cls else None,
            sentiment=cls.sentiment if cls else None,
            sentiment_score=cls.sentiment_score if cls else None,
            relevance=cls.relevance if cls else None,
            importance=cls.importance if cls else None,
            importance_score=cls.importance_score if cls else None,
            should_index=cls.should_index if cls else None,
            should_alert=cls.should_alert if cls else None,
            is_significant_event=cls.is_significant_event if cls else None,
            explanation=cls.explanation if cls else None,
            hashtags=[h.tag for h in p.hashtags],
            entities=[EntityInfo(name=e.name, entity_type=e.entity_type) for e in p.entities],
            mentioned_users=[m.username for m in p.mentioned_users],
            extracted_urls=[],
        )


# ═══════════════════════════════════════════════════════════════════════════
#  SEARCH SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class SearchService:
    """Multi‑filter search across posts."""

    async def search(
        self,
        keyword: Optional[str] = None,
        username: Optional[str] = None,
        hashtag: Optional[str] = None,
        topic: Optional[str] = None,
        sentiment: Optional[str] = None,
        importance: Optional[str] = None,
        min_relevance: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PostResponse]:
        async with async_session() as session:
            query = (
                select(Post)
                .join(Classification, Classification.post_id == Post.id)
                .options(
                    selectinload(Post.classification),
                    selectinload(Post.hashtags),
                    selectinload(Post.entities),
                    selectinload(Post.mentioned_users),
                )
            )

            conditions = []
            if keyword:
                conditions.append(Post.text.ilike(f"%{keyword}%"))
            if username:
                conditions.append(Post.author_username.ilike(f"%{username}%"))
            if topic:
                conditions.append(Classification.category.ilike(f"%{topic}%"))
            if sentiment:
                conditions.append(Classification.sentiment == sentiment)
            if importance:
                conditions.append(Classification.importance == importance)
            if min_relevance is not None:
                conditions.append(Classification.relevance >= min_relevance)
            if start_date:
                conditions.append(Post.timestamp >= start_date)
            if end_date:
                conditions.append(Post.timestamp <= end_date)

            if hashtag:
                query = query.join(Hashtag, Hashtag.post_id == Post.id)
                conditions.append(Hashtag.tag.ilike(f"%{hashtag}%"))

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(desc(Post.timestamp)).offset(offset).limit(limit)
            result = await session.execute(query)
            posts = result.scalars().unique().all()
            return [EventsService._post_to_response(p) for p in posts]


# ═══════════════════════════════════════════════════════════════════════════
#  ALERTS SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class AlertsService:
    """CRUD for user‑defined alerts."""

    async def create_alert(self, name: str, conditions: Dict[str, Any]) -> int:
        async with async_session() as session:
            async with session.begin():
                alert = Alert(name=name, conditions=conditions)
                session.add(alert)
                await session.flush()
                return alert.id

    async def list_alerts(self) -> List[Dict[str, Any]]:
        async with async_session() as session:
            result = await session.execute(select(Alert).order_by(desc(Alert.created_at)))
            alerts = result.scalars().all()
            return [
                {"id": a.id, "name": a.name, "conditions": a.conditions, "active": a.active, "created_at": a.created_at.isoformat()}
                for a in alerts
            ]

    async def delete_alert(self, alert_id: int) -> bool:
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(Alert).where(Alert.id == alert_id))
                alert = result.scalars().first()
                if alert:
                    await session.delete(alert)
                    return True
                return False

    async def get_notifications(self, limit: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
        async with async_session() as session:
            query = select(AlertNotification).order_by(desc(AlertNotification.created_at)).limit(limit)
            if unread_only:
                query = query.where(AlertNotification.read == False)
            result = await session.execute(query)
            notifs = result.scalars().all()
            return [
                {"id": n.id, "alert_id": n.alert_id, "post_id": n.post_id, "message": n.message, "read": n.read, "created_at": n.created_at.isoformat()}
                for n in notifs
            ]

    async def mark_read(self, notification_id: int) -> None:
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(AlertNotification).where(AlertNotification.id == notification_id)
                )
                notif = result.scalars().first()
                if notif:
                    notif.read = True


# ═══════════════════════════════════════════════════════════════════════════
#  POSTS SERVICE
# ═══════════════════════════════════════════════════════════════════════════
class PostsService:
    """Fetch posts with various filters."""

    async def get_recent(self, limit: int = 50) -> List[PostResponse]:
        async with async_session() as session:
            result = await session.execute(
                select(Post)
                .options(
                    selectinload(Post.classification),
                    selectinload(Post.hashtags),
                    selectinload(Post.entities),
                    selectinload(Post.mentioned_users),
                )
                .order_by(desc(Post.timestamp))
                .limit(limit)
            )
            posts = result.scalars().all()
            return [EventsService._post_to_response(p) for p in posts]

    async def get_by_topic(self, topic: str, limit: int = 50) -> List[PostResponse]:
        async with async_session() as session:
            result = await session.execute(
                select(Post)
                .join(Classification, Classification.post_id == Post.id)
                .where(Classification.category.ilike(f"%{topic}%"))
                .options(
                    selectinload(Post.classification),
                    selectinload(Post.hashtags),
                    selectinload(Post.entities),
                    selectinload(Post.mentioned_users),
                )
                .order_by(desc(Post.timestamp))
                .limit(limit)
            )
            posts = result.scalars().all()
            return [EventsService._post_to_response(p) for p in posts]

    async def get_post(self, post_id: int) -> Optional[PostResponse]:
        async with async_session() as session:
            result = await session.execute(
                select(Post)
                .where(Post.id == post_id)
                .options(
                    selectinload(Post.classification),
                    selectinload(Post.hashtags),
                    selectinload(Post.entities),
                    selectinload(Post.mentioned_users),
                )
            )
            post = result.scalars().first()
            if post:
                return EventsService._post_to_response(post)
            return None
