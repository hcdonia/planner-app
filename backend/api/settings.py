"""Settings API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.knowledge_service import KnowledgeService
from ..services.memory_service import MemoryService
from ..models.schemas import (
    CalendarResponse,
    KnowledgeResponse,
    AIInstructionResponse,
    SchedulingRuleResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/all")
def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings in one call (for settings page)."""
    knowledge_service = KnowledgeService(db)
    memory_service = MemoryService(db)

    calendars = knowledge_service.get_all_calendars()
    knowledge = knowledge_service.get_all_knowledge()
    instructions = knowledge_service.get_all_instructions()
    rules = knowledge_service.get_all_rules()
    patterns = memory_service.analyze_task_patterns()

    return {
        "calendars": [CalendarResponse.model_validate(c) for c in calendars],
        "knowledge": [KnowledgeResponse.model_validate(k) for k in knowledge],
        "instructions": [AIInstructionResponse.model_validate(i) for i in instructions],
        "rules": [SchedulingRuleResponse.model_validate(r) for r in rules],
        "patterns": patterns,
    }


@router.get("/patterns")
def get_patterns(db: Session = Depends(get_db)):
    """Get learned patterns from task history."""
    memory_service = MemoryService(db)
    return memory_service.analyze_task_patterns()


@router.post("/initialize")
def initialize_default_calendars(db: Session = Depends(get_db)):
    """Initialize default calendars (for first-time setup)."""
    from ..services.calendar_service import CalendarService

    knowledge_service = KnowledgeService(db)
    calendar_service = CalendarService(db)

    # Check if we already have calendars
    existing = knowledge_service.get_all_calendars()
    if existing:
        return {"message": "Calendars already configured", "calendars": existing}

    # Get available Google calendars
    try:
        google_cals = calendar_service.get_all_google_calendars()
    except Exception as e:
        return {"error": f"Could not connect to Google Calendar: {str(e)}"}

    # Default calendars to look for
    default_names = [
        ("Personal", "read"),
        ("Work", "read"),
        ("Mastermind", "read"),
        ("Modern Stylist Movement Calendar", "read"),
        ("Project Manager", "read_write"),
    ]

    added = []
    for name, permission in default_names:
        if name in google_cals:
            calendar = knowledge_service.add_calendar(
                name=name,
                google_calendar_id=google_cals[name],
                permission=permission,
            )
            added.append(CalendarResponse.model_validate(calendar))

    return {
        "message": f"Added {len(added)} calendars",
        "calendars": added,
        "available": list(google_cals.keys()),
    }


@router.delete("/reset")
def reset_all_settings(db: Session = Depends(get_db)):
    """Reset all settings (dangerous - use with caution)."""
    from ..models.database import Calendar, Knowledge, AIInstruction, SchedulingRule

    db.query(Calendar).delete()
    db.query(Knowledge).delete()
    db.query(AIInstruction).delete()
    db.query(SchedulingRule).delete()
    db.commit()

    return {"message": "All settings reset"}


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    """Check system health and configuration status."""
    from ..config import get_settings
    from ..services.calendar_service import CalendarService

    settings = get_settings()
    knowledge_service = KnowledgeService(db)

    # Determine database type
    if settings.DATABASE_URL:
        db_type = "PostgreSQL"
    else:
        db_type = "SQLite local storage"

    status = {
        "openai": {"status": "unknown", "model": settings.OPENAI_MODEL},
        "google_calendar": {"status": "unknown"},
        "database": {"status": "ok", "type": db_type},
        "calendars_configured": 0,
        "knowledge_entries": 0,
    }

    # Check OpenAI
    if settings.OPENAI_API_KEY:
        if settings.OPENAI_API_KEY.startswith("sk-"):
            status["openai"]["status"] = "configured"
        else:
            status["openai"]["status"] = "invalid_key_format"
    else:
        status["openai"]["status"] = "not_configured"
        status["openai"]["message"] = "Set OPENAI_API_KEY in .env file"

    # Check Google Calendar
    try:
        calendar_service = CalendarService(db)
        cals = calendar_service.get_all_google_calendars()
        status["google_calendar"]["status"] = "connected"
        status["google_calendar"]["available_calendars"] = len(cals)
    except FileNotFoundError:
        status["google_calendar"]["status"] = "missing_credentials"
        status["google_calendar"]["message"] = "Missing credentials.json - download from Google Cloud Console"
    except Exception as e:
        status["google_calendar"]["status"] = "error"
        status["google_calendar"]["message"] = str(e)

    # Check configured calendars
    calendars = knowledge_service.get_all_calendars()
    status["calendars_configured"] = len(calendars)
    status["writable_calendar"] = any(c.permission == "read_write" for c in calendars)

    # Check knowledge
    knowledge = knowledge_service.get_all_knowledge()
    status["knowledge_entries"] = len(knowledge)

    # Overall status
    all_ok = (
        status["openai"]["status"] == "configured" and
        status["google_calendar"]["status"] == "connected" and
        status["calendars_configured"] > 0 and
        status["writable_calendar"]
    )
    status["overall"] = "ready" if all_ok else "needs_setup"

    return status
