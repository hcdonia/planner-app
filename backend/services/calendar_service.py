"""Google Calendar service - refactored from app.py."""
import os
import json
import base64
import datetime as dt
from typing import List, Optional, Tuple, Dict, Any
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.database import Calendar

settings = get_settings()


class CalendarService:
    """Service for Google Calendar operations."""

    def __init__(self, db: Session):
        self.db = db
        self._service = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes

    @property
    def service(self):
        """Lazy-load Google Calendar service."""
        if self._service is None:
            self._service = self._authenticate()
        return self._service

    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        creds = None

        # Check for base64-encoded credentials from environment (for cloud deployment)
        if settings.GOOGLE_TOKEN_JSON:
            try:
                token_data = base64.b64decode(settings.GOOGLE_TOKEN_JSON).decode('utf-8')
                token_dict = json.loads(token_data)
                creds = Credentials.from_authorized_user_info(token_dict, settings.GOOGLE_SCOPES)
            except Exception as e:
                raise RuntimeError(f"Failed to load token from GOOGLE_TOKEN_JSON: {e}")
        else:
            # Fallback to file-based auth for local development
            token_path = str(settings.TOKEN_PATH)
            creds_path = str(settings.CREDENTIALS_PATH)

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, settings.GOOGLE_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif not settings.GOOGLE_TOKEN_JSON:
                # Only try OAuth flow for local development
                creds_path = str(settings.CREDENTIALS_PATH)
                if not os.path.exists(creds_path):
                    raise RuntimeError(
                        f"Missing credentials.json at {creds_path}. "
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, settings.GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)

                with open(str(settings.TOKEN_PATH), "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def get_all_google_calendars(self) -> Dict[str, str]:
        """Get all calendars from Google account. Returns {name: id}."""
        page_token = None
        cal_map = {}

        while True:
            calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
            for item in calendar_list.get("items", []):
                cal_map[item.get("summary")] = item.get("id")
            page_token = calendar_list.get("nextPageToken")
            if not page_token:
                break

        return cal_map

    def get_active_calendars(self) -> List[Calendar]:
        """Get all active calendars from database."""
        return self.db.query(Calendar).filter(Calendar.active == True).all()

    def get_calendar_ids(self) -> Tuple[List[str], Optional[str]]:
        """Get calendar IDs for all active calendars.

        Returns:
            Tuple of (read_calendar_ids, write_calendar_id)
        """
        calendars = self.get_active_calendars()
        read_ids = []
        write_id = None

        for cal in calendars:
            read_ids.append(cal.google_calendar_id)
            if cal.permission == "read_write" and write_id is None:
                write_id = cal.google_calendar_id

        return read_ids, write_id

    def fetch_busy(
        self,
        calendar_ids: List[str],
        time_min: dt.datetime,
        time_max: dt.datetime,
    ) -> List[Tuple[dt.datetime, dt.datetime]]:
        """Fetch busy periods from calendars."""
        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": cid} for cid in calendar_ids],
        }
        resp = self.service.freebusy().query(body=body).execute()

        busy = []
        for cid in calendar_ids:
            for item in resp.get("calendars", {}).get(cid, {}).get("busy", []):
                start = dt.datetime.fromisoformat(item["start"].replace("Z", "+00:00"))
                end = dt.datetime.fromisoformat(item["end"].replace("Z", "+00:00"))
                busy.append((start, end))

        busy.sort(key=lambda x: x[0])
        return busy

    def get_events(
        self,
        calendar_ids: List[str],
        time_min: dt.datetime,
        time_max: dt.datetime,
    ) -> List[Dict[str, Any]]:
        """Get actual events (not just busy times) from calendars."""
        events = []

        for cid in calendar_ids:
            result = (
                self.service.events()
                .list(
                    calendarId=cid,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            for event in result.get("items", []):
                start = event.get("start", {})
                end = event.get("end", {})

                # Handle all-day events vs timed events
                tz = ZoneInfo(settings.TIMEZONE)
                if "dateTime" in start:
                    start_dt = dt.datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
                    end_dt = dt.datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
                else:
                    # All-day event - add timezone to make it comparable
                    start_dt = dt.datetime.strptime(start["date"], "%Y-%m-%d").replace(tzinfo=tz)
                    end_dt = dt.datetime.strptime(end["date"], "%Y-%m-%d").replace(tzinfo=tz)

                events.append({
                    "id": event.get("id"),
                    "summary": event.get("summary", "(No title)"),
                    "start": start_dt,
                    "end": end_dt,
                    "calendar_id": cid,
                    "description": event.get("description"),
                    "location": event.get("location"),
                })

        events.sort(key=lambda x: x["start"])
        return events

    def get_day_schedule(self, date: dt.date) -> List[Dict[str, Any]]:
        """Get all events for a specific day."""
        tz = ZoneInfo(settings.TIMEZONE)
        time_min = dt.datetime(date.year, date.month, date.day, 0, 0, tzinfo=tz)
        time_max = dt.datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=tz)

        calendar_ids, _ = self.get_calendar_ids()
        return self.get_events(calendar_ids, time_min, time_max)

    def get_week_overview(self, start_date: Optional[dt.date] = None) -> Dict[str, List[Dict]]:
        """Get overview of the week's schedule."""
        tz = ZoneInfo(settings.TIMEZONE)
        if start_date is None:
            start_date = dt.datetime.now(tz).date()

        # Find Monday of this week
        days_since_monday = start_date.weekday()
        monday = start_date - dt.timedelta(days=days_since_monday)

        overview = {}
        for i in range(7):
            day = monday + dt.timedelta(days=i)
            day_name = day.strftime("%A")
            overview[day_name] = self.get_day_schedule(day)

        return overview

    def within_working_hours(
        self,
        day: dt.date,
        allow_outside: bool = False,
        earliest_hour: Optional[int] = None,
        latest_hour: Optional[int] = None,
        deadline: Optional[dt.datetime] = None,
        work_start: Optional[int] = None,
        work_end: Optional[int] = None,
        workdays: set = None,
    ) -> Optional[Tuple[dt.datetime, dt.datetime]]:
        """Calculate the working window for a given day."""
        if workdays is None:
            workdays = {0, 1, 2, 3, 4, 5, 6}  # All days by default

        # Use settings for default work hours
        if work_start is None:
            work_start = settings.WORK_START_HOUR
        if work_end is None:
            work_end = settings.WORK_END_HOUR

        tz = ZoneInfo(settings.TIMEZONE)
        weekday = day.weekday()

        if not allow_outside:
            if weekday not in workdays:
                return None
            start_hour = work_start
            end_hour = work_end
        else:
            # Extended hours but still reasonable (8am - 8pm)
            start_hour = 8
            end_hour = 20

        if earliest_hour is not None:
            start_hour = max(start_hour, earliest_hour)
        if latest_hour is not None:
            end_hour = min(end_hour, latest_hour)

        start = dt.datetime(day.year, day.month, day.day, start_hour, 0, tzinfo=tz)
        end = dt.datetime(day.year, day.month, day.day, end_hour, 0, tzinfo=tz)

        if deadline and day == deadline.date():
            end = min(end, deadline)

        if start >= end:
            return None
        return start, end

    def find_available_slots(
        self,
        duration_minutes: int,
        start_at: Optional[dt.datetime] = None,
        days_ahead: int = 14,
        allow_outside: bool = False,
        earliest_hour: Optional[int] = None,
        latest_hour: Optional[int] = None,
        deadline: Optional[dt.datetime] = None,
        num_slots: int = 3,
    ) -> List[Tuple[dt.datetime, dt.datetime]]:
        """Find multiple available time slots."""
        tz = ZoneInfo(settings.TIMEZONE)
        if start_at is None:
            start_at = dt.datetime.now(tz) + dt.timedelta(minutes=5)

        duration = dt.timedelta(minutes=duration_minutes)
        today = start_at.date()
        end_date = today + dt.timedelta(days=days_ahead)
        if deadline:
            end_date = min(end_date, deadline.date())

        # Fetch busy times
        calendar_ids, _ = self.get_calendar_ids()
        time_min = start_at
        time_max = dt.datetime(end_date.year, end_date.month, end_date.day, 23, 59, tzinfo=tz)
        busy = self.fetch_busy(calendar_ids, time_min, time_max)

        slots = []

        for day_offset in range(days_ahead + 1):
            day = today + dt.timedelta(days=day_offset)
            if day > end_date:
                break

            window = self.within_working_hours(
                day, allow_outside, earliest_hour, latest_hour, deadline
            )
            if not window:
                continue

            day_start, day_end = window
            if day == today:
                day_start = max(day_start, start_at)
            if day_start >= day_end:
                continue

            # Filter busy intervals for this day
            day_busy = []
            for bstart, bend in busy:
                if bend <= day_start or bstart >= day_end:
                    continue
                day_busy.append((max(bstart, day_start), min(bend, day_end)))
            day_busy.sort(key=lambda x: x[0])

            cursor = day_start
            for bstart, bend in day_busy:
                if bstart - cursor >= duration:
                    slots.append((cursor, cursor + duration))
                    if len(slots) >= num_slots:
                        return slots
                cursor = max(cursor, bend)

            if day_end - cursor >= duration:
                slots.append((cursor, cursor + duration))
                if len(slots) >= num_slots:
                    return slots

        return slots

    def find_first_slot(
        self,
        duration_minutes: int,
        start_at: Optional[dt.datetime] = None,
        days_ahead: int = 14,
        allow_outside: bool = False,
        earliest_hour: Optional[int] = None,
        latest_hour: Optional[int] = None,
        deadline: Optional[dt.datetime] = None,
    ) -> Tuple[Optional[dt.datetime], Optional[dt.datetime]]:
        """Find the first available time slot."""
        slots = self.find_available_slots(
            duration_minutes=duration_minutes,
            start_at=start_at,
            days_ahead=days_ahead,
            allow_outside=allow_outside,
            earliest_hour=earliest_hour,
            latest_hour=latest_hour,
            deadline=deadline,
            num_slots=1,
        )
        if slots:
            return slots[0]
        return None, None

    def create_event(
        self,
        title: str,
        start: dt.datetime,
        end: dt.datetime,
        calendar_id: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an event on the calendar."""
        if calendar_id is None:
            _, calendar_id = self.get_calendar_ids()
            if calendar_id is None:
                raise RuntimeError("No writable calendar configured")

        event = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": settings.TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": settings.TIMEZONE},
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location

        created = self.service.events().insert(calendarId=calendar_id, body=event).execute()
        return created

    def update_event(
        self,
        event_id: str,
        calendar_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an existing event."""
        # Get current event
        event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Apply updates
        if "title" in updates:
            event["summary"] = updates["title"]
        if "start" in updates:
            event["start"] = {"dateTime": updates["start"].isoformat(), "timeZone": settings.TIMEZONE}
        if "end" in updates:
            event["end"] = {"dateTime": updates["end"].isoformat(), "timeZone": settings.TIMEZONE}
        if "description" in updates:
            event["description"] = updates["description"]
        if "location" in updates:
            event["location"] = updates["location"]

        updated = self.service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()
        return updated

    def delete_event(self, event_id: str, calendar_id: str) -> None:
        """Delete an event."""
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def format_schedule_summary(self, events: List[Dict]) -> str:
        """Format a list of events into a readable summary."""
        if not events:
            return "No events scheduled."

        lines = []
        for event in events:
            start = event["start"]
            if isinstance(start, dt.datetime):
                time_str = start.strftime("%I:%M %p")
            else:
                time_str = "All day"

            duration = ""
            if isinstance(event["start"], dt.datetime) and isinstance(event["end"], dt.datetime):
                mins = int((event["end"] - event["start"]).total_seconds() / 60)
                if mins >= 60:
                    hours = mins // 60
                    remaining = mins % 60
                    duration = f" ({hours}h{remaining}m)" if remaining else f" ({hours}h)"
                else:
                    duration = f" ({mins}m)"

            lines.append(f"- {time_str}: {event['summary']}{duration}")

        return "\n".join(lines)
