import os
import re
import json
import datetime as dt
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import requests
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

import tkinter as tk
from tkinter import messagebox

# -----------------------------
# User settings
# -----------------------------
TIMEZONE = "America/New_York"
WORKDAYS = {0, 1, 2, 3, 4}  # Mon-Fri
WORK_START_HOUR = 9
WORK_END_HOUR = 17

CALENDAR_NAMES = [
    "Personal",
    "Work",
    "Mastermind",
    "Modern Stylist Movement Calendar",
]
PROJECT_CALENDAR_NAME = "Project Manager"

SEARCH_DAYS_AHEAD = 14

# -----------------------------
# OpenAI config
# -----------------------------
OPENAI_MODEL = "gpt-5"
OPENAI_API_URL = "https://api.openai.com/v1/responses"

# -----------------------------
# Google Calendar scopes
# -----------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]


@dataclass
class Task:
    title: str = ""
    priority: str = ""
    duration_minutes: Optional[int] = None
    allow_outside_hours: bool = False
    earliest_hour: Optional[int] = None
    latest_hour: Optional[int] = None
    deadline: Optional[dt.datetime] = None
    suggested_start: Optional[dt.datetime] = None
    suggested_end: Optional[dt.datetime] = None


@dataclass
class AppState:
    stage: str = "await_task"
    task: Task = field(default_factory=Task)
    calendars_ready: bool = False


def load_env():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Add it to a .env file or your shell.")
    return api_key


def get_creds():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise RuntimeError("Missing credentials.json. Download from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def get_calendar_ids(service) -> Tuple[List[str], str]:
    page_token = None
    cal_map = {}
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for item in calendar_list.get("items", []):
            cal_map[item.get("summary")] = item.get("id")
        page_token = calendar_list.get("nextPageToken")
        if not page_token:
            break

    missing = [name for name in CALENDAR_NAMES if name not in cal_map]
    if missing:
        raise RuntimeError(f"Could not find calendars: {', '.join(missing)}")

    if PROJECT_CALENDAR_NAME not in cal_map:
        raise RuntimeError(
            f"Could not find project calendar: {PROJECT_CALENDAR_NAME}"
        )

    calendar_ids = [cal_map[name] for name in CALENDAR_NAMES]
    project_id = cal_map[PROJECT_CALENDAR_NAME]
    return calendar_ids, project_id


def fetch_busy(service, calendar_ids: List[str], time_min: dt.datetime, time_max: dt.datetime):
    body = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "items": [{"id": cid} for cid in calendar_ids],
    }
    resp = service.freebusy().query(body=body).execute()
    busy = []
    for cid in calendar_ids:
        for item in resp.get("calendars", {}).get(cid, {}).get("busy", []):
            start = dt.datetime.fromisoformat(item["start"].replace("Z", "+00:00"))
            end = dt.datetime.fromisoformat(item["end"].replace("Z", "+00:00"))
            busy.append((start, end))
    busy.sort(key=lambda x: x[0])
    return busy


def within_working_hours(
    day: dt.date,
    allow_outside: bool,
    earliest_hour: Optional[int],
    latest_hour: Optional[int],
    deadline: Optional[dt.datetime],
) -> Optional[Tuple[dt.datetime, dt.datetime]]:
    tz = ZoneInfo(TIMEZONE)
    weekday = day.weekday()
    if not allow_outside:
        if weekday not in WORKDAYS:
            return None
        start_hour = WORK_START_HOUR
        end_hour = WORK_END_HOUR
    else:
        # Outside-hours allowed: include weekends and a broader day window
        start_hour = 7
        end_hour = 21

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


def find_first_slot(
    busy,
    duration_min: int,
    start_at: dt.datetime,
    days_ahead: int,
    allow_outside: bool,
    earliest_hour: Optional[int],
    latest_hour: Optional[int],
    deadline: Optional[dt.datetime],
):
    tz = ZoneInfo(TIMEZONE)
    duration = dt.timedelta(minutes=duration_min)
    today = start_at.date()
    end_date = today + dt.timedelta(days=days_ahead)
    if deadline:
        end_date = min(end_date, deadline.date())

    for day_offset in range(days_ahead + 1):
        day = today + dt.timedelta(days=day_offset)
        if day > end_date:
            break
        window = within_working_hours(day, allow_outside, earliest_hour, latest_hour, deadline)
        if not window:
            continue
        day_start, day_end = window
        if day == today:
            day_start = max(day_start, start_at)
        if day_start >= day_end:
            continue

        # Filter busy intervals that intersect this day
        day_busy = []
        for bstart, bend in busy:
            if bend <= day_start or bstart >= day_end:
                continue
            day_busy.append((max(bstart, day_start), min(bend, day_end)))
        day_busy.sort(key=lambda x: x[0])

        cursor = day_start
        for bstart, bend in day_busy:
            if bstart - cursor >= duration:
                return cursor, cursor + duration
            cursor = max(cursor, bend)
        if day_end - cursor >= duration:
            return cursor, cursor + duration

    return None, None


def parse_priority(text: str) -> Optional[str]:
    t = text.strip().lower()
    if t in {"high", "h", "1"}:
        return "High"
    if t in {"medium", "med", "m", "2"}:
        return "Medium"
    if t in {"low", "l", "3"}:
        return "Low"
    return None


def parse_duration(text: str) -> Optional[int]:
    t = text.strip().lower()
    if not t:
        return None
    if "guess" in t or "not sure" in t or "idk" in t:
        return None

    # Hours
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours)", t)
    if hour_match:
        hours = float(hour_match.group(1))
        return int(round(hours * 60))

    # Minutes
    min_match = re.search(r"(\d+)\s*(m|min|mins|minute|minutes)", t)
    if min_match:
        return int(min_match.group(1))

    # Bare number = minutes
    if t.isdigit():
        return int(t)

    return None


def parse_yes_no(text: str) -> Optional[bool]:
    t = text.strip().lower()
    if t in {"yes", "y", "ok", "okay"}:
        return True
    if t in {"no", "n"}:
        return False
    return None


def parse_time_hour(text: str) -> Optional[int]:
    t = text.strip().lower()
    match = re.search(r"(\\d{1,2})(?::(\\d{2}))?\\s*(am|pm)?", t)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        suffix = match.group(3)
    else:
        m = re.search(r"\\d{1,2}", t)
        if not m:
            return None
        hour = int(m.group(0))
        minute = 0
        suffix = None
    if suffix:
        if suffix == "pm" and hour != 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
    else:
        if hour <= 12:
            hour += 12
    if 0 <= hour <= 23:
        return hour
    return None


def infer_deadline(text: str) -> Optional[dt.datetime]:
    t = text.lower()
    if "end of the month" in t or "end of month" in t:
        now = dt.datetime.now(ZoneInfo(TIMEZONE))
        next_month = now.replace(day=28) + dt.timedelta(days=4)
        last_day = next_month - dt.timedelta(days=next_month.day)
        return dt.datetime(last_day.year, last_day.month, last_day.day, 23, 59, tzinfo=ZoneInfo(TIMEZONE))
    return None


def gpt_guess_duration(api_key: str, title: str) -> int:
    prompt = (
        "Estimate a reasonable duration in minutes for this task title. "
        "Return only a single integer. Keep it between 15 and 240 minutes.\n\n"
        f"Task: {title}"
    )
    payload = {
        "model": OPENAI_MODEL,
        "input": prompt,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(OPENAI_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        text = data["output"][0]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        text = "60"
    match = re.search(r"\d+", str(text))
    minutes = int(match.group(0)) if match else 60
    return max(15, min(240, minutes))


def format_dt(d: dt.datetime) -> str:
    return d.strftime("%a %b %d, %Y at %I:%M %p")


class PlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Planner")

        self.state = AppState()
        self.api_key = None
        self.service = None
        self.calendar_ids = []
        self.project_id = ""

        self.chat = tk.Text(root, state="disabled", width=80, height=24, wrap="word")
        self.chat.pack(padx=10, pady=10)

        self.entry = tk.Entry(root, width=80)
        self.entry.pack(padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.on_send)

        self.send_btn = tk.Button(root, text="Send", command=self.on_send)
        self.send_btn.pack(padx=10, pady=(0, 10))

        self.bootstrap()

    def bootstrap(self):
        try:
            self.api_key = load_env()
            creds = get_creds()
            self.service = build("calendar", "v3", credentials=creds)
            self.calendar_ids, self.project_id = get_calendar_ids(self.service)
            self.state.calendars_ready = True
        except Exception as e:
            messagebox.showerror("Setup Error", str(e))
            self.root.destroy()
            return

        self.add_msg("assistant", "Hi! Tell me a task you want to schedule.")

    def add_msg(self, role, text):
        self.chat.configure(state="normal")
        prefix = "You: " if role == "user" else "Assistant: "
        self.chat.insert("end", f"{prefix}{text}\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def on_send(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.add_msg("user", text)
        self.handle_input(text)

    def handle_input(self, text: str):
        stage = self.state.stage

        if stage == "await_task":
            task = Task(title=text)
            task.deadline = infer_deadline(text)
            if "after work" in text.lower():
                task.allow_outside_hours = True
                task.earliest_hour = WORK_END_HOUR
            initial_duration = parse_duration(text)
            if initial_duration:
                task.duration_minutes = initial_duration
            self.state.task = task
            self.state.stage = "await_priority"
            self.add_msg("assistant", "What priority is this? (High / Medium / Low)")
            return

        if stage == "await_priority":
            pr = parse_priority(text)
            if not pr:
                self.add_msg("assistant", "Please reply with High, Medium, or Low.")
                return
            self.state.task.priority = pr
            if self.state.task.duration_minutes:
                self.state.stage = "await_duration_confirm"
                self.add_msg(
                    "assistant",
                    f"I heard about {self.state.task.duration_minutes} minutes. Is that okay? (yes/no)",
                )
                return
            self.state.stage = "await_duration"
            self.add_msg(
                "assistant",
                "How long will it take? (examples: 30 min, 1.5 hours). If you’re not sure, say ‘guess’.",
            )
            return

        if stage == "await_duration":
            duration = parse_duration(text)
            if duration is None:
                duration = gpt_guess_duration(self.api_key, self.state.task.title)
                self.add_msg(
                    "assistant",
                    f"I can guess about {duration} minutes. Is that okay? (yes/no)",
                )
                self.state.task.duration_minutes = duration
                self.state.stage = "await_duration_confirm"
                return

            self.state.task.duration_minutes = duration
            self.state.stage = "await_outside"
            self.add_msg(
                "assistant",
                "Keep it within work hours (Mon–Fri 9–5)? (yes/no)",
            )
            return

        if stage == "await_duration_confirm":
            if text.strip().lower() in {"yes", "y", "ok", "okay"}:
                if self.state.task.allow_outside_hours:
                    if self.state.task.latest_hour is None:
                        self.state.stage = "await_latest_time"
                        self.add_msg(
                            "assistant",
                            "Got it. What’s the latest time you’d accept? (e.g., 8pm)",
                        )
                    else:
                        self.suggest_slot()
                else:
                    self.state.stage = "await_outside"
                    self.add_msg(
                        "assistant",
                        "Keep it within work hours (Mon–Fri 9–5)? (yes/no)",
                    )
                return
            if text.strip().lower() in {"no", "n"}:
                self.state.stage = "await_duration"
                self.add_msg(
                    "assistant",
                    "Okay — how long will it take? (examples: 30 min, 1.5 hours)",
                )
                return
            self.add_msg("assistant", "Please reply yes or no.")
            return

        if stage == "await_outside":
            yn = parse_yes_no(text)
            if yn is None:
                self.add_msg("assistant", "Please reply yes or no.")
                return
            # Question: "Keep it within work hours?"
            self.state.task.allow_outside_hours = False if yn else True
            if self.state.task.allow_outside_hours and self.state.task.latest_hour is None:
                self.state.stage = "await_latest_time"
                self.add_msg(
                    "assistant",
                    "What’s the latest time you’d accept? (e.g., 8pm)",
                )
                return
            self.suggest_slot()
            return

        if stage == "await_latest_time":
            hour = parse_time_hour(text)
            if hour is None:
                self.add_msg("assistant", "Please give a time like 5pm, 17, or 20:00.")
                return
            self.state.task.latest_hour = hour
            self.suggest_slot()
            return

        if stage == "await_expand":
            yn = parse_yes_no(text)
            if yn is None:
                self.add_msg("assistant", "Please reply yes or no.")
                return
            if yn:
                self.state.task.allow_outside_hours = True
                self.suggest_slot()
                return
            self.add_msg("assistant", "Okay — tell me a new task when you’re ready.")
            self.reset_flow()
            return

        if stage == "await_confirm":
            if text.strip().lower() in {"yes", "y", "ok", "okay"}:
                self.create_event()
                self.reset_flow()
                return
            if text.strip().lower() in {"no", "n"}:
                self.add_msg("assistant", "No problem. Tell me a new task when you’re ready.")
                self.reset_flow()
                return
            if "too late" in text.lower() or "earlier" in text.lower():
                self.state.stage = "await_latest_time"
                self.add_msg("assistant", "Got it. What’s the latest time you’d accept? (e.g., 8pm)")
                return
            self.add_msg("assistant", "Please reply yes or no.")
            return

    def suggest_slot(self):
        now = dt.datetime.now(ZoneInfo(TIMEZONE)) + dt.timedelta(minutes=5)
        start_window = now
        end_window = now + dt.timedelta(days=SEARCH_DAYS_AHEAD)
        busy = fetch_busy(self.service, self.calendar_ids + [self.project_id], start_window, end_window)

        start, end = find_first_slot(
            busy,
            self.state.task.duration_minutes,
            start_window,
            SEARCH_DAYS_AHEAD,
            self.state.task.allow_outside_hours,
            self.state.task.earliest_hour,
            self.state.task.latest_hour,
            self.state.task.deadline,
        )

        if not start:
            self.add_msg(
                "assistant",
                "I couldn’t find a slot in the next two weeks. Try outside hours and weekends? (yes/no)",
            )
            self.state.stage = "await_expand"
            return

        self.state.task.suggested_start = start
        self.state.task.suggested_end = end
        self.state.stage = "await_confirm"

        self.add_msg(
            "assistant",
            f"I suggest {format_dt(start)} for {self.state.task.duration_minutes} minutes. Should I add it to your {PROJECT_CALENDAR_NAME} calendar? (yes/no)",
        )

    def create_event(self):
        t = self.state.task
        event = {
            "summary": t.title,
            "description": f"Priority: {t.priority}\nDuration: {t.duration_minutes} minutes",
            "start": {"dateTime": t.suggested_start.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": t.suggested_end.isoformat(), "timeZone": TIMEZONE},
        }
        self.service.events().insert(calendarId=self.project_id, body=event).execute()
        self.add_msg("assistant", "Done! It’s on your Project Management calendar.")

    def reset_flow(self):
        self.state.stage = "await_task"
        self.state.task = Task()


def main():
    root = tk.Tk()
    app = PlannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
