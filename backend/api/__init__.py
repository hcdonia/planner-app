"""API routes package."""
from .chat import router as chat_router
from .calendar import router as calendar_router
from .knowledge import router as knowledge_router
from .settings import router as settings_router
from .todos import router as todos_router
from .files import router as files_router

__all__ = ["chat_router", "calendar_router", "knowledge_router", "settings_router", "todos_router", "files_router"]
