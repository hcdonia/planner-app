"""Memory service - manages conversations and message history."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.database import Conversation, Message, TaskHistory


class MemoryService:
    """Service for managing conversation memory and task history."""

    def __init__(self, db: Session):
        self.db = db

    # ============ Conversation Operations ============

    def create_conversation(self, title: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_recent_conversations(self, limit: int = 10) -> List[Conversation]:
        """Get recent conversations."""
        return (
            self.db.query(Conversation)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .all()
        )

    def update_conversation(
        self,
        conversation_id: int,
        title: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Optional[Conversation]:
        """Update conversation metadata."""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            if title is not None:
                conversation.title = title
            if summary is not None:
                conversation.summary = summary
            conversation.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(conversation)
        return conversation

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages."""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False

    # ============ Message Operations ============

    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Save a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            extra_data=metadata,
        )
        self.db.add(message)

        # Update conversation's updated_at
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """Get messages for a conversation."""
        query = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 20,
    ) -> List[Message]:
        """Get the most recent messages from a conversation."""
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(desc(Message.timestamp))
            .limit(limit)
            .all()
        )
        # Return in chronological order
        return list(reversed(messages))

    def search_messages(self, query: str, limit: int = 10) -> List[Message]:
        """Search messages across all conversations."""
        return (
            self.db.query(Message)
            .filter(Message.content.ilike(f"%{query}%"))
            .order_by(desc(Message.timestamp))
            .limit(limit)
            .all()
        )

    # ============ Task History Operations ============

    def add_task_history(
        self,
        title: str,
        duration_minutes: int,
        scheduled_at: datetime,
        category: Optional[str] = None,
        google_event_id: Optional[str] = None,
        calendar_name: Optional[str] = None,
    ) -> TaskHistory:
        """Record a scheduled task."""
        task = TaskHistory(
            title=title,
            duration_minutes=duration_minutes,
            scheduled_at=scheduled_at,
            category=category,
            google_event_id=google_event_id,
            calendar_name=calendar_name,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task_history(self, limit: int = 50) -> List[TaskHistory]:
        """Get recent task history."""
        return (
            self.db.query(TaskHistory)
            .order_by(desc(TaskHistory.scheduled_at))
            .limit(limit)
            .all()
        )

    def get_tasks_by_category(self, category: str) -> List[TaskHistory]:
        """Get all tasks for a category."""
        return (
            self.db.query(TaskHistory)
            .filter(TaskHistory.category == category)
            .order_by(desc(TaskHistory.scheduled_at))
            .all()
        )

    def mark_task_completed(
        self,
        task_id: int,
        actual_duration: Optional[int] = None,
    ) -> Optional[TaskHistory]:
        """Mark a task as completed."""
        task = self.db.query(TaskHistory).filter(TaskHistory.id == task_id).first()
        if task:
            task.completed = True
            if actual_duration is not None:
                task.actual_duration_minutes = actual_duration
            self.db.commit()
            self.db.refresh(task)
        return task

    def analyze_task_patterns(self) -> dict:
        """Analyze task history for patterns."""
        tasks = self.get_task_history(limit=100)

        if not tasks:
            return {"patterns": []}

        patterns = {}

        # Duration patterns by category
        category_durations = {}
        for task in tasks:
            if task.category:
                if task.category not in category_durations:
                    category_durations[task.category] = []
                category_durations[task.category].append(task.duration_minutes)

        for category, durations in category_durations.items():
            avg = sum(durations) / len(durations)
            patterns[f"{category}_typical_duration"] = round(avg / 15) * 15

        # Time-of-day preferences
        morning_tasks = [t for t in tasks if t.scheduled_at.hour < 12]
        afternoon_tasks = [t for t in tasks if 12 <= t.scheduled_at.hour < 17]
        evening_tasks = [t for t in tasks if t.scheduled_at.hour >= 17]

        total = len(tasks)
        if total > 0:
            patterns["morning_percentage"] = len(morning_tasks) / total
            patterns["afternoon_percentage"] = len(afternoon_tasks) / total
            patterns["evening_percentage"] = len(evening_tasks) / total

            if len(morning_tasks) > len(afternoon_tasks) * 1.5:
                patterns["time_preference"] = "morning"
            elif len(afternoon_tasks) > len(morning_tasks) * 1.5:
                patterns["time_preference"] = "afternoon"

        return {"patterns": patterns, "task_count": len(tasks)}

    def get_context_for_ai(self, conversation_id: int, max_messages: int = 20) -> dict:
        """Get full context for AI including conversation history and patterns."""
        messages = self.get_recent_messages(conversation_id, limit=max_messages)
        patterns = self.analyze_task_patterns()

        return {
            "messages": [
                {"role": m.role, "content": m.content, "extra_data": m.extra_data}
                for m in messages
            ],
            "patterns": patterns,
        }
