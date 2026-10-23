"""
Pydantic schemas for API request / response serialisation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# ── Raw post coming from a stream provider ────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class RawPost(BaseModel):
    external_id: str
    author_name: str
    author_username: str
    author_avatar: str = ""
    text: str
    timestamp: datetime
    url: str = ""
    likes: int = 0
    reposts: int = 0
    replies: int = 0
    views: int = 0
    raw_data: Dict[str, Any] = {}


# ═══════════════════════════════════════════════════════════════════════════
# ── Classification result from Laya / classifier ─────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class ClassificationResult(BaseModel):
    category: str
    sentiment: str                  # positive | negative | neutral
    sentiment_score: float = 0.0    # -1 … +1
    relevance: float = 0.0         # 0 … 100
    importance: str = "LOW"         # LOW | MEDIUM | HIGH | CRITICAL
    importance_score: float = 0.0   # 0 … 100
    should_index: bool = True
    should_alert: bool = False
    is_significant_event: bool = False
    explanation: str = ""
    entities: List[EntityInfo] = []
    raw_output: Dict[str, Any] = {}


class EntityInfo(BaseModel):
    name: str
    entity_type: str = "UNKNOWN"    # ORG | PERSON | PRODUCT | TECH | …


# Allow forward‑ref resolution
ClassificationResult.model_rebuild()


# ═══════════════════════════════════════════════════════════════════════════
# ── API response models ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class PostResponse(BaseModel):
    id: int
    external_id: str
    author_name: str
    author_username: str
    author_avatar: str
    text: str
    timestamp: datetime
    url: str
    likes: int
    reposts: int
    replies: int
    views: int
    processing_timestamp: Optional[datetime] = None
    # classification
    category: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    relevance: Optional[float] = None
    importance: Optional[str] = None
    importance_score: Optional[float] = None
    should_index: Optional[bool] = None
    should_alert: Optional[bool] = None
    is_significant_event: Optional[bool] = None
    explanation: Optional[str] = None
    # extracted
    hashtags: List[str] = []
    entities: List[EntityInfo] = []
    mentioned_users: List[str] = []
    extracted_urls: List[str] = []

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    severity: str
    first_detected: datetime
    last_updated: Optional[datetime] = None
    post_count: int
    status: str
    related_entities: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: int
    name: str
    conditions: Dict[str, Any]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertNotificationResponse(BaseModel):
    id: int
    alert_id: int
    post_id: int
    message: Optional[str] = None
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════
# ── Dashboard stats ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class DashboardStats(BaseModel):
    posts_received: int = 0
    posts_analyzed: int = 0
    posts_indexed: int = 0
    alerts_generated: int = 0
    posts_per_minute: float = 0.0
    avg_latency_ms: float = 0.0
    is_live: bool = True
    stream_mode: str = "mock"


# ═══════════════════════════════════════════════════════════════════════════
# ── Analytics ────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class SentimentBreakdown(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0


class TopicCount(BaseModel):
    topic: str
    count: int


class ActivityPoint(BaseModel):
    timestamp: str
    count: int


class ImportanceBreakdown(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class TrendingEntity(BaseModel):
    name: str
    count: int
    velocity: float = 0.0      # mentions‑per‑minute delta
    trend: str = "stable"       # rising | falling | stable


class AnalyticsResponse(BaseModel):
    sentiment: SentimentBreakdown
    topics: List[TopicCount]
    activity: List[ActivityPoint]
    importance: ImportanceBreakdown
    trending_entities: List[TrendingEntity]


# ═══════════════════════════════════════════════════════════════════════════
# ── RAG ──────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class RAGRequest(BaseModel):
    question: str
    time_range_hours: Optional[float] = None


class RAGCitation(BaseModel):
    post_id: int
    author_username: str
    text: str
    timestamp: datetime
    relevance_score: float


class RAGResponse(BaseModel):
    answer: str
    citations: List[RAGCitation] = []
    query_time_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# ── Search ───────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class SearchRequest(BaseModel):
    keyword: Optional[str] = None
    username: Optional[str] = None
    hashtag: Optional[str] = None
    topic: Optional[str] = None
    sentiment: Optional[str] = None
    importance: Optional[str] = None
    min_relevance: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=200)
    offset: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# ── Alert creation ───────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class CreateAlertRequest(BaseModel):
    name: str
    conditions: Dict[str, Any]
    # conditions example:
    # {"topic": "AI", "min_relevance": 90, "importance": "HIGH"}


# ═══════════════════════════════════════════════════════════════════════════
# ── WebSocket messages ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════
class WSMessage(BaseModel):
    type: str   # "new_post" | "stats_update" | "new_event" | "new_alert"
    data: Any
