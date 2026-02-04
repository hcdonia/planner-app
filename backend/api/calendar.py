"""Calendar API endpoints."""
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from ..database import get_db
from ..config import get_settings
from ..services.calendar_service import CalendarService
from ..services.knowledge_service import KnowledgeService
from ..models.schemas import (
    CalendarCreate,
    CalendarUpdate,
    CalendarResponse,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])
settings = get_settings()


@router.get("/google-calendars")
def list_google_calendars(db: Session = Depends(get_db)):
    """List all available Google Calendars from the user's account."""
    try:
        calendar_service = CalendarService(db)
        calendars = calendar_service.get_all_google_calendars()
        return {
            "calendars": [
                {"name": name, "id": cal_id}
                for name, cal_id in calendars.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tracked", response_model=list[CalendarResponse])
def list_tracked_calendars(db: Session = Depends(get_db)):
    """List all calendars being tracked in the app."""
    knowledge_service = KnowledgeService(db)
    return knowledge_service.get_all_calendars()


@router.post("/tracked", response_model=CalendarResponse)
def add_tracked_calendar(
    calendar: CalendarCreate,
    db: Session = Depends(get_db),
):
    """Add a calendar to track."""
    knowledge_service = KnowledgeService(db)
    return knowledge_service.add_calendar(
        name=calendar.name,
        google_calendar_id=calendar.google_calendar_id,
        permission=calendar.permission,
        color=calendar.color,
        priority=calendar.priority,
    )


@router.put("/tracked/{calendar_id}", response_model=CalendarResponse)
def update_tracked_calendar(
    calendar_id: int,
    updates: CalendarUpdate,
    db: Session = Depends(get_db),
):
    """Update a tracked calendar's settings."""
    knowledge_service = KnowledgeService(db)
    calendar = knowledge_service.update_calendar(
        calendar_id,
        updates.model_dump(exclude_unset=True),
    )
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar


@router.delete("/tracked/{calendar_id}")
def remove_tracked_calendar(
    calendar_id: int,
    db: Session = Depends(get_db),
):
    """Stop tracking a calendar."""
    knowledge_service = KnowledgeService(db)
    success = knowledge_service.remove_calendar(calendar_id)
    if not success:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return {"success": True}


@router.get("/schedule/today")
def get_today_schedule(db: Session = Depends(get_db)):
    """Get today's schedule."""
    try:
        calendar_service = CalendarService(db)
        tz = ZoneInfo(settings.TIMEZONE)
        today = dt.datetime.now(tz).date()
        events = calendar_service.get_day_schedule(today)

        return {
            "date": today.isoformat(),
            "events": [
                {
                    "id": e.get("id"),
                    "title": e["summary"],
                    "start": e["start"].isoformat() if isinstance(e["start"], dt.datetime) else e["start"],
                    "end": e["end"].isoformat() if isinstance(e["end"], dt.datetime) else e["end"],
                    "calendar_id": e.get("calendar_id"),
                }
                for e in events
            ],
            "summary": calendar_service.format_schedule_summary(events),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/{date}")
def get_date_schedule(
    date: str,
    db: Session = Depends(get_db),
):
    """Get schedule for a specific date (YYYY-MM-DD)."""
    try:
        parsed_date = dt.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        calendar_service = CalendarService(db)
        events = calendar_service.get_day_schedule(parsed_date)

        return {
            "date": parsed_date.isoformat(),
            "events": [
                {
                    "id": e.get("id"),
                    "title": e["summary"],
                    "start": e["start"].isoformat() if isinstance(e["start"], dt.datetime) else e["start"],
                    "end": e["end"].isoformat() if isinstance(e["end"], dt.datetime) else e["end"],
                }
                for e in events
            ],
            "summary": calendar_service.format_schedule_summary(events),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/week")
def get_week_overview(
    start_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get week overview."""
    parsed_date = None
    if start_date:
        try:
            parsed_date = dt.datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        calendar_service = CalendarService(db)
        overview = calendar_service.get_week_overview(parsed_date)

        formatted = {}
        for day, events in overview.items():
            formatted[day] = {
                "events": [
                    {
                        "title": e["summary"],
                        "start": e["start"].isoformat() if isinstance(e["start"], dt.datetime) else e["start"],
                        "end": e["end"].isoformat() if isinstance(e["end"], dt.datetime) else e["end"],
                    }
                    for e in events
                ],
                "summary": calendar_service.format_schedule_summary(events),
            }

        return {"week": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/availability")
def check_availability(
    duration_minutes: int,
    allow_outside_hours: bool = False,
    num_slots: int = 5,
    db: Session = Depends(get_db),
):
    """Check availability for scheduling."""
    try:
        calendar_service = CalendarService(db)
        slots = calendar_service.find_available_slots(
            duration_minutes=duration_minutes,
            allow_outside=allow_outside_hours,
            num_slots=num_slots,
        )

        return {
            "slots": [
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "formatted": start.strftime("%A, %B %d at %I:%M %p"),
                }
                for start, end in slots
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
