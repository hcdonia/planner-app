"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


# ============ Calendar Schemas ============

class CalendarBase(BaseModel):
    name: str
    google_calendar_id: str
    permission: str = "read"
    color: Optional[str] = None
    priority: int = 5
    active: bool = True


class CalendarCreate(CalendarBase):
    pass


class CalendarUpdate(BaseModel):
    name: Optional[str] = None
    google_calendar_id: Optional[str] = None
    permission: Optional[str] = None
    color: Optional[str] = None
    priority: Optional[int] = None
    active: Optional[bool] = None


class CalendarResponse(CalendarBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Knowledge Schemas ============

class KnowledgeBase(BaseModel):
    category: str
    subject: str
    content: str
    source: str = "conversation"
    confidence: float = 1.0


class KnowledgeCreate(KnowledgeBase):
    pass


class KnowledgeUpdate(BaseModel):
    category: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    active: Optional[bool] = None


class KnowledgeResponse(KnowledgeBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ AI Instruction Schemas ============

class AIInstructionBase(BaseModel):
    category: str
    instruction: str
    source: str = "user"


class AIInstructionCreate(AIInstructionBase):
    pass


class AIInstructionUpdate(BaseModel):
    category: Optional[str] = None
    instruction: Optional[str] = None
    source: Optional[str] = None
    active: Optional[bool] = None


class AIInstructionResponse(AIInstructionBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Scheduling Rule Schemas ============

class SchedulingRuleBase(BaseModel):
    rule_type: str
    name: str
    config: dict


class SchedulingRuleCreate(SchedulingRuleBase):
    pass


class SchedulingRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    name: Optional[str] = None
    config: Optional[dict] = None
    active: Optional[bool] = None


class SchedulingRuleResponse(SchedulingRuleBase):
    id: int
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Conversation/Message Schemas ============

class MessageBase(BaseModel):
    role: str
    content: str
    extra_data: Optional[dict] = None


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: int
    summary: Optional[str] = None
    started_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    started_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ============ Chat Schemas ============

class ChatMessage(BaseModel):
    """Incoming chat message from frontend."""
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    """Response to send back to frontend."""
    type: str  # 'chunk', 'complete', 'error', 'function_call'
    content: Optional[str] = None
    conversation_id: Optional[int] = None
    metadata: Optional[dict] = None


# ============ Task History Schemas ============

class TaskHistoryBase(BaseModel):
    title: str
    category: Optional[str] = None
    duration_minutes: int
    scheduled_at: datetime
    google_event_id: Optional[str] = None
    calendar_name: Optional[str] = None


class TaskHistoryCreate(TaskHistoryBase):
    pass


class TaskHistoryResponse(TaskHistoryBase):
    id: int
    completed: bool
    actual_duration_minutes: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Todo Item Schemas ============

class TodoItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # 'high', 'medium', 'low'
    due_date: Optional[datetime] = None
    estimated_minutes: Optional[int] = None


class TodoItemCreate(TodoItemBase):
    pass


class TodoItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    completed: Optional[bool] = None


class TodoItemResponse(TodoItemBase):
    id: int
    completed: bool
    completed_at: Optional[datetime] = None
    scheduled_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
