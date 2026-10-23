"""
SQLAlchemy async database engine, session factory, and all ORM models.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from config import settings

# ── Engine & session ────────────────────────────────────────────────────────
connect_args = {"timeout": 30.0} if "sqlite" in settings.database_url else {}
engine = create_async_engine(settings.database_url, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ── Posts ────────────────────────────────────────────────────────────────────
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(64), unique=True, index=True, nullable=False)
    author_name = Column(String(128))
    author_username = Column(String(64), index=True)
    author_avatar = Column(String(512))
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    url = Column(String(512))
    likes = Column(Integer, default=0)
    reposts = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    views = Column(Integer, default=0)
    processing_timestamp = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    classification = relationship(
        "Classification", back_populates="post", uselist=False, cascade="all, delete-orphan"
    )
    hashtags = relationship("Hashtag", back_populates="post", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="post", cascade="all, delete-orphan")
    mentioned_users = relationship(
        "MentionedUser", back_populates="post", cascade="all, delete-orphan"
    )
    extracted_urls = relationship(
        "ExtractedUrl", back_populates="post", cascade="all, delete-orphan"
    )
    embedding_record = relationship(
        "EmbeddingRecord", back_populates="post", uselist=False, cascade="all, delete-orphan"
    )


# ── Classification ──────────────────────────────────────────────────────────
class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True, nullable=False)
    category = Column(String(64), index=True)
    sentiment = Column(String(16))           # positive | negative | neutral
    sentiment_score = Column(Float)          # -1.0 … +1.0
    relevance = Column(Float)               # 0 … 100
    importance = Column(String(16))          # LOW | MEDIUM | HIGH | CRITICAL
    importance_score = Column(Float)         # 0 … 100
    should_index = Column(Boolean, default=True)
    should_alert = Column(Boolean, default=False)
    is_significant_event = Column(Boolean, default=False)
    explanation = Column(Text)
    raw_output = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="classification")


# ── Hashtags ────────────────────────────────────────────────────────────────
class Hashtag(Base):
    __tablename__ = "hashtags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(128), index=True, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    post = relationship("Post", back_populates="hashtags")


# ── Entities ────────────────────────────────────────────────────────────────
class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), index=True, nullable=False)
    entity_type = Column(String(64))         # ORG | PERSON | PRODUCT | TECH | …
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    post = relationship("Post", back_populates="entities")


# ── Mentioned users ────────────────────────────────────────────────────────
class MentionedUser(Base):
    __tablename__ = "mentioned_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), index=True, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    post = relationship("Post", back_populates="mentioned_users")


# ── Extracted URLs ──────────────────────────────────────────────────────────
class ExtractedUrl(Base):
    __tablename__ = "extracted_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(512), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    post = relationship("Post", back_populates="extracted_urls")


# ── Embedding records (pointer to vector store) ────────────────────────────
class EmbeddingRecord(Base):
    __tablename__ = "embedding_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), unique=True, nullable=False)
    embedding_id = Column(String(64), unique=True, nullable=False)
    model_name = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="embedding_record")


# ── Events ──────────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    description = Column(Text)
    category = Column(String(64))
    severity = Column(String(16), default="HIGH")  # LOW | MEDIUM | HIGH | CRITICAL
    first_detected = Column(DateTime, nullable=False)
    last_updated = Column(DateTime)
    post_count = Column(Integer, default=0)
    status = Column(String(16), default="active")  # active | resolved | dismissed
    related_entities = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class EventPost(Base):
    __tablename__ = "event_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)


# ── Alerts ──────────────────────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    conditions = Column(JSON, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    message = Column(Text)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Topic configuration ────────────────────────────────────────────────────
class TopicConfig(Base):
    __tablename__ = "topic_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    keywords = Column(JSON)
    color = Column(String(16), default="#6366f1")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


from sqlalchemy import text

# ── Helpers ─────────────────────────────────────────────────────────────────
async def init_db():
    """Create all tables and configure SQLite pragmas."""
    async with engine.begin() as conn:
        if "sqlite" in settings.database_url:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA busy_timeout=10000;"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session
