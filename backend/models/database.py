"""SQLAlchemy database models."""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from ..database import Base


class Calendar(Base):
    """Dynamic calendar configuration."""

    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    google_calendar_id = Column(String(255), nullable=False)
    permission = Column(String(20), default="read")  # 'read' or 'read_write'
    color = Column(String(20), nullable=True)
    priority = Column(Integer, default=5)  # 1-10, lower = higher priority
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIInstruction(Base):
    """AI's self-modifiable instructions."""

    __tablename__ = "ai_instructions"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # 'system', 'scheduling', 'communication'
    instruction = Column(Text, nullable=False)
    source = Column(String(50), default="user")  # 'user', 'ai_learned', 'default'
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Knowledge(Base):
    """Knowledge entries - facts the AI knows about the user."""

    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)  # 'business', 'people', 'preferences', 'task_types'
    subject = Column(String(255), nullable=False)  # What this is about
    content = Column(Text, nullable=False)  # The actual knowledge
    source = Column(String(50), default="conversation")  # 'conversation', 'inferred', 'settings'
    confidence = Column(Float, default=1.0)  # For learned/inferred knowledge
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchedulingRule(Base):
    """Dynamic scheduling constraints and preferences."""

    __tablename__ = "scheduling_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False)  # 'time_block', 'buffer', 'preference'
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=False)  # Flexible rule configuration
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    """Conversation sessions."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated summary
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual chat messages."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, nullable=True)  # Function calls, actions taken
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")


class TaskHistory(Base):
    """Record of scheduled tasks for pattern learning."""

    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # AI-inferred category
    duration_minutes = Column(Integer, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False)
    actual_duration_minutes = Column(Integer, nullable=True)  # If tracked
    google_event_id = Column(String(255), nullable=True)
    calendar_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TodoItem(Base):
    """To-do list items - quick tasks that can be scheduled later."""

    __tablename__ = "todo_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")  # 'high', 'medium', 'low'
    start_date = Column(DateTime, nullable=True)  # When to start working on it
    due_date = Column(DateTime, nullable=True)  # Deadline
    estimated_minutes = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    scheduled_event_id = Column(String(255), nullable=True)  # Link to Google Calendar event if scheduled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
