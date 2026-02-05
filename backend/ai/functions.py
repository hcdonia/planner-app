"""AI function definitions for GPT function calling."""
import datetime as dt
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from ..config import get_settings
from ..services.calendar_service import CalendarService
from ..services.knowledge_service import KnowledgeService
from ..services.memory_service import MemoryService
from ..models.database import TodoItem

settings = get_settings()


# Function definitions for OpenAI
AI_FUNCTIONS = [
    # ============ Calendar Operations ============
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check calendar availability for scheduling. Returns available time slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of the event in minutes",
                    },
                    "date_preference": {
                        "type": "string",
                        "description": "Preferred date or date range (e.g., 'tomorrow', 'next week', 'Monday')",
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Preferred time of day (e.g., 'morning', 'afternoon', '2pm')",
                    },
                    "allow_outside_hours": {
                        "type": "boolean",
                        "description": "Whether to include times outside normal work hours",
                        "default": False,
                    },
                },
                "required": ["duration_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "Schedule a task on the calendar. Always confirm with user before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the event",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO format (e.g., '2024-01-15T14:00:00')",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description for the event",
                    },
                },
                "required": ["title", "start_time", "duration_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_day_schedule",
            "description": "Get all events scheduled for a specific day",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format, or 'today', 'tomorrow'",
                    },
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_week_overview",
            "description": "Get an overview of the week's schedule",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (defaults to today)",
                    },
                },
                "required": [],
            },
        },
    },
    # ============ Knowledge Management ============
    {
        "type": "function",
        "function": {
            "name": "save_knowledge",
            "description": "Save important information about the user for future reference",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["business", "people", "preferences", "task_types", "general"],
                        "description": "Category of the knowledge",
                    },
                    "subject": {
                        "type": "string",
                        "description": "What this knowledge is about (e.g., 'Modern Stylist Movement', 'Sarah')",
                    },
                    "content": {
                        "type": "string",
                        "description": "The actual information to remember",
                    },
                },
                "required": ["category", "subject", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge",
            "description": "Search for stored knowledge about a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_knowledge",
            "description": "Update existing knowledge entry",
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_id": {
                        "type": "integer",
                        "description": "ID of the knowledge entry to update",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the knowledge entry",
                    },
                },
                "required": ["knowledge_id", "content"],
            },
        },
    },
    # ============ Self-Modification ============
    {
        "type": "function",
        "function": {
            "name": "add_instruction",
            "description": "Add a new instruction for how to behave. Use when user tells you to change behavior.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["scheduling", "communication", "preferences", "behavior"],
                        "description": "Category of the instruction",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "The instruction to follow",
                    },
                },
                "required": ["category", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_scheduling_rule",
            "description": "Add a scheduling constraint or preference",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule_type": {
                        "type": "string",
                        "enum": ["time_block", "buffer", "preference", "constraint"],
                        "description": "Type of scheduling rule",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the rule (e.g., 'No meetings before 10am')",
                    },
                    "config": {
                        "type": "object",
                        "description": "Rule configuration (e.g., {earliest_hour: 10})",
                    },
                },
                "required": ["rule_type", "name", "config"],
            },
        },
    },
    # ============ Calendar Configuration ============
    {
        "type": "function",
        "function": {
            "name": "add_calendar",
            "description": "Add a new Google Calendar to track",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Display name for the calendar",
                    },
                    "google_calendar_id": {
                        "type": "string",
                        "description": "Google Calendar ID (email format or calendar ID)",
                    },
                    "permission": {
                        "type": "string",
                        "enum": ["read", "read_write"],
                        "description": "Permission level",
                        "default": "read",
                    },
                },
                "required": ["name", "google_calendar_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_google_calendars",
            "description": "List all available Google Calendars from the user's account",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_calendar",
            "description": "Stop tracking a calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "integer",
                        "description": "Database ID of the calendar to remove",
                    },
                },
                "required": ["calendar_id"],
            },
        },
    },
    # ============ Todo List Operations ============
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "Add a new task to the to-do list",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the task",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description or notes for the task",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Priority level of the task",
                        "default": "medium",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "When to start working on the task (ISO format or natural language like 'tomorrow', 'next Monday')",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Deadline for the task (ISO format or natural language)",
                    },
                    "estimated_minutes": {
                        "type": "integer",
                        "description": "Estimated time to complete in minutes",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_todos",
            "description": "Get all tasks from the to-do list",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_completed": {
                        "type": "boolean",
                        "description": "Whether to include completed tasks",
                        "default": False,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_todo",
            "description": "Update an existing to-do item",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "integer",
                        "description": "ID of the todo to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "New priority",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "New start date",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "New due date",
                    },
                    "completed": {
                        "type": "boolean",
                        "description": "Mark as completed or incomplete",
                    },
                },
                "required": ["todo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_todo",
            "description": "Delete a to-do item",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "integer",
                        "description": "ID of the todo to delete",
                    },
                },
                "required": ["todo_id"],
            },
        },
    },
]


def execute_function(
    db: Session,
    function_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a function and return the result."""
    calendar_service = CalendarService(db)
    knowledge_service = KnowledgeService(db)
    memory_service = MemoryService(db)
    tz = ZoneInfo(settings.TIMEZONE)

    try:
        # ============ Calendar Operations ============
        if function_name == "check_availability":
            duration = arguments.get("duration_minutes", 30)
            allow_outside = arguments.get("allow_outside_hours", False)
            date_pref = arguments.get("date_preference", "")
            time_pref = arguments.get("time_preference", "")

            # Parse date preference
            start_at = None
            now = dt.datetime.now(tz)

            if date_pref:
                date_lower = date_pref.lower()
                if "today" in date_lower:
                    start_at = now
                elif "tomorrow" in date_lower:
                    start_at = now + dt.timedelta(days=1)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "monday" in date_lower:
                    days_ahead = (0 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "tuesday" in date_lower:
                    days_ahead = (1 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "wednesday" in date_lower:
                    days_ahead = (2 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "thursday" in date_lower:
                    days_ahead = (3 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "friday" in date_lower:
                    days_ahead = (4 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "saturday" in date_lower:
                    days_ahead = (5 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "sunday" in date_lower:
                    days_ahead = (6 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)
                elif "next week" in date_lower:
                    days_ahead = (0 - now.weekday()) % 7 + 7  # Next Monday
                    start_at = now + dt.timedelta(days=days_ahead)
                    start_at = start_at.replace(hour=0, minute=0)

            # Parse time preference for earliest_hour
            earliest_hour = None
            latest_hour = None
            if time_pref:
                time_lower = time_pref.lower()
                if "morning" in time_lower:
                    earliest_hour = 7
                    latest_hour = 12
                elif "afternoon" in time_lower:
                    earliest_hour = 12
                    latest_hour = 17
                elif "evening" in time_lower or "after work" in time_lower:
                    earliest_hour = 17
                    latest_hour = 21
                    allow_outside = True

            # Default to reasonable daytime hours if no preference given
            if earliest_hour is None:
                earliest_hour = settings.WORK_START_HOUR
            if latest_hour is None:
                latest_hour = settings.WORK_END_HOUR

            slots = calendar_service.find_available_slots(
                duration_minutes=duration,
                start_at=start_at,
                allow_outside=allow_outside,
                earliest_hour=earliest_hour,
                latest_hour=latest_hour,
                num_slots=5,
            )

            if not slots:
                return {
                    "success": False,
                    "message": "No available slots found in the next 14 days",
                }

            formatted_slots = []
            # Collect unique dates from slots to fetch existing events
            slot_dates = set()
            for start, end in slots:
                formatted_slots.append({
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "formatted": start.strftime("%A, %B %d at %I:%M %p"),
                })
                slot_dates.add(start.date())

            # Fetch existing events for those days so the AI has real context
            existing_events = {}
            for day in sorted(slot_dates):
                day_events = calendar_service.get_day_schedule(day)
                if day_events:
                    day_label = day.strftime("%A, %B %d")
                    existing_events[day_label] = [
                        {
                            "title": e["summary"],
                            "time": f"{e['start'].strftime('%I:%M %p') if isinstance(e['start'], dt.datetime) else e['start']} - {e['end'].strftime('%I:%M %p') if isinstance(e['end'], dt.datetime) else e['end']}",
                        }
                        for e in day_events
                    ]

            return {
                "success": True,
                "available_slots": formatted_slots,
                "existing_events_by_day": existing_events,
                "message": f"Found {len(formatted_slots)} available slots. IMPORTANT: The 'available_slots' are guaranteed free times with no conflicts. The 'existing_events_by_day' shows what is ALREADY scheduled. Do NOT suggest times that overlap with existing events. Only offer the exact times listed in 'available_slots'.",
            }

        elif function_name == "schedule_task":
            title = arguments["title"]
            start_str = arguments["start_time"]
            duration = arguments["duration_minutes"]
            description = arguments.get("description")

            # Parse start time
            start = dt.datetime.fromisoformat(start_str)
            if start.tzinfo is None:
                start = start.replace(tzinfo=tz)
            end = start + dt.timedelta(minutes=duration)

            # Create event
            event = calendar_service.create_event(
                title=title,
                start=start,
                end=end,
                description=description,
            )

            # Record in task history
            memory_service.add_task_history(
                title=title,
                duration_minutes=duration,
                scheduled_at=start,
                google_event_id=event.get("id"),
            )

            return {
                "success": True,
                "message": f"Scheduled '{title}' for {start.strftime('%A, %B %d at %I:%M %p')}",
                "event_id": event.get("id"),
            }

        elif function_name == "get_day_schedule":
            date_str = arguments.get("date", "today")

            if date_str == "today":
                date = dt.datetime.now(tz).date()
            elif date_str == "tomorrow":
                date = dt.datetime.now(tz).date() + dt.timedelta(days=1)
            else:
                date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()

            events = calendar_service.get_day_schedule(date)
            summary = calendar_service.format_schedule_summary(events)

            return {
                "success": True,
                "date": date.isoformat(),
                "events": [
                    {
                        "title": e["summary"],
                        "start": e["start"].isoformat() if isinstance(e["start"], dt.datetime) else e["start"],
                        "end": e["end"].isoformat() if isinstance(e["end"], dt.datetime) else e["end"],
                    }
                    for e in events
                ],
                "summary": summary,
            }

        elif function_name == "get_week_overview":
            start_str = arguments.get("start_date")
            start_date = None
            if start_str:
                start_date = dt.datetime.strptime(start_str, "%Y-%m-%d").date()

            overview = calendar_service.get_week_overview(start_date)

            formatted = {}
            for day, events in overview.items():
                formatted[day] = calendar_service.format_schedule_summary(events)

            return {
                "success": True,
                "overview": formatted,
            }

        # ============ Knowledge Operations ============
        elif function_name == "save_knowledge":
            knowledge = knowledge_service.save_knowledge(
                category=arguments["category"],
                subject=arguments["subject"],
                content=arguments["content"],
            )
            return {
                "success": True,
                "message": f"Saved knowledge about '{arguments['subject']}'",
                "knowledge_id": knowledge.id,
            }

        elif function_name == "get_knowledge":
            results = knowledge_service.get_knowledge(arguments["query"])
            return {
                "success": True,
                "results": [
                    {
                        "id": k.id,
                        "category": k.category,
                        "subject": k.subject,
                        "content": k.content,
                    }
                    for k in results
                ],
            }

        elif function_name == "update_knowledge":
            knowledge = knowledge_service.update_knowledge(
                arguments["knowledge_id"],
                arguments["content"],
            )
            if knowledge:
                return {
                    "success": True,
                    "message": f"Updated knowledge about '{knowledge.subject}'",
                }
            return {"success": False, "message": "Knowledge entry not found"}

        # ============ Self-Modification ============
        elif function_name == "add_instruction":
            instruction = knowledge_service.add_instruction(
                category=arguments["category"],
                instruction=arguments["instruction"],
                source="ai_learned",
            )
            return {
                "success": True,
                "message": f"Added instruction: {arguments['instruction']}",
                "instruction_id": instruction.id,
            }

        elif function_name == "add_scheduling_rule":
            rule = knowledge_service.add_scheduling_rule(
                rule_type=arguments["rule_type"],
                name=arguments["name"],
                config=arguments["config"],
            )
            return {
                "success": True,
                "message": f"Added scheduling rule: {arguments['name']}",
                "rule_id": rule.id,
            }

        # ============ Calendar Configuration ============
        elif function_name == "add_calendar":
            calendar = knowledge_service.add_calendar(
                name=arguments["name"],
                google_calendar_id=arguments["google_calendar_id"],
                permission=arguments.get("permission", "read"),
            )
            return {
                "success": True,
                "message": f"Added calendar '{arguments['name']}'",
                "calendar_id": calendar.id,
            }

        elif function_name == "list_google_calendars":
            calendars = calendar_service.get_all_google_calendars()
            return {
                "success": True,
                "calendars": [
                    {"name": name, "id": cal_id}
                    for name, cal_id in calendars.items()
                ],
            }

        elif function_name == "remove_calendar":
            success = knowledge_service.remove_calendar(arguments["calendar_id"])
            return {
                "success": success,
                "message": "Calendar removed" if success else "Calendar not found",
            }

        # ============ Todo List Operations ============
        elif function_name == "add_todo":
            title = arguments["title"]
            description = arguments.get("description")
            priority = arguments.get("priority", "medium")
            start_date_str = arguments.get("start_date")
            due_date_str = arguments.get("due_date")
            estimated_minutes = arguments.get("estimated_minutes")

            # Parse dates
            now = dt.datetime.now(tz)
            start_date = None
            due_date = None

            def parse_date_string(date_str: str) -> Optional[dt.datetime]:
                if not date_str:
                    return None
                date_lower = date_str.lower()
                # Try ISO format first
                try:
                    parsed = dt.datetime.fromisoformat(date_str)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=tz)
                    return parsed
                except ValueError:
                    pass
                # Natural language parsing
                if "today" in date_lower:
                    return now.replace(hour=9, minute=0, second=0, microsecond=0)
                elif "tomorrow" in date_lower:
                    return (now + dt.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                elif "next week" in date_lower:
                    days_ahead = (0 - now.weekday()) % 7 + 7
                    return (now + dt.timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
                # Check for day names
                days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                for i, day in enumerate(days):
                    if day in date_lower:
                        days_ahead = (i - now.weekday()) % 7
                        if days_ahead == 0:
                            days_ahead = 7
                        return (now + dt.timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
                return None

            start_date = parse_date_string(start_date_str) if start_date_str else None
            due_date = parse_date_string(due_date_str) if due_date_str else None

            # Create the todo
            todo = TodoItem(
                title=title,
                description=description,
                priority=priority,
                start_date=start_date,
                due_date=due_date,
                estimated_minutes=estimated_minutes,
            )
            db.add(todo)
            db.commit()
            db.refresh(todo)

            response_parts = [f"Added '{title}' to your to-do list"]
            if start_date:
                response_parts.append(f"starting {start_date.strftime('%A, %B %d')}")
            if due_date:
                response_parts.append(f"due {due_date.strftime('%A, %B %d')}")

            return {
                "success": True,
                "message": ", ".join(response_parts),
                "todo_id": todo.id,
            }

        elif function_name == "get_todos":
            include_completed = arguments.get("include_completed", False)
            query = db.query(TodoItem)
            if not include_completed:
                query = query.filter(TodoItem.completed == False)
            todos = query.all()

            return {
                "success": True,
                "todos": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "priority": t.priority,
                        "start_date": t.start_date.isoformat() if t.start_date else None,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "completed": t.completed,
                    }
                    for t in todos
                ],
            }

        elif function_name == "update_todo":
            todo_id = arguments["todo_id"]
            todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
            if not todo:
                return {"success": False, "message": f"Todo with ID {todo_id} not found"}

            # Update fields
            if "title" in arguments:
                todo.title = arguments["title"]
            if "description" in arguments:
                todo.description = arguments["description"]
            if "priority" in arguments:
                todo.priority = arguments["priority"]
            if "start_date" in arguments:
                start_date_str = arguments["start_date"]
                if start_date_str:
                    def parse_date_string(date_str: str) -> Optional[dt.datetime]:
                        if not date_str:
                            return None
                        date_lower = date_str.lower()
                        try:
                            parsed = dt.datetime.fromisoformat(date_str)
                            if parsed.tzinfo is None:
                                parsed = parsed.replace(tzinfo=tz)
                            return parsed
                        except ValueError:
                            pass
                        if "today" in date_lower:
                            return now.replace(hour=9, minute=0, second=0, microsecond=0)
                        elif "tomorrow" in date_lower:
                            return (now + dt.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                        for i, day in enumerate(days):
                            if day in date_lower:
                                days_ahead = (i - now.weekday()) % 7
                                if days_ahead == 0:
                                    days_ahead = 7
                                return (now + dt.timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
                        return None
                    todo.start_date = parse_date_string(start_date_str)
                else:
                    todo.start_date = None
            if "due_date" in arguments:
                due_date_str = arguments["due_date"]
                if due_date_str:
                    def parse_date_string(date_str: str) -> Optional[dt.datetime]:
                        if not date_str:
                            return None
                        date_lower = date_str.lower()
                        try:
                            parsed = dt.datetime.fromisoformat(date_str)
                            if parsed.tzinfo is None:
                                parsed = parsed.replace(tzinfo=tz)
                            return parsed
                        except ValueError:
                            pass
                        if "today" in date_lower:
                            return now.replace(hour=9, minute=0, second=0, microsecond=0)
                        elif "tomorrow" in date_lower:
                            return (now + dt.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                        for i, day in enumerate(days):
                            if day in date_lower:
                                days_ahead = (i - now.weekday()) % 7
                                if days_ahead == 0:
                                    days_ahead = 7
                                return (now + dt.timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
                        return None
                    todo.due_date = parse_date_string(due_date_str)
                else:
                    todo.due_date = None
            if "completed" in arguments:
                todo.completed = arguments["completed"]
                if todo.completed:
                    todo.completed_at = dt.datetime.now(tz)
                else:
                    todo.completed_at = None

            db.commit()
            return {
                "success": True,
                "message": f"Updated todo '{todo.title}'",
            }

        elif function_name == "delete_todo":
            todo_id = arguments["todo_id"]
            todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
            if not todo:
                return {"success": False, "message": f"Todo with ID {todo_id} not found"}

            title = todo.title
            db.delete(todo)
            db.commit()
            return {
                "success": True,
                "message": f"Deleted todo '{title}'",
            }

        else:
            return {"success": False, "error": f"Unknown function: {function_name}"}

    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error executing function {function_name}: {e}\n{traceback.format_exc()}")

        # Provide helpful error messages for common issues
        error_msg = str(e)
        if "quota" in error_msg.lower() or "rate" in error_msg.lower():
            return {
                "success": False,
                "error": "API rate limit reached. Please wait a moment and try again.",
                "error_type": "rate_limit"
            }
        elif "credential" in error_msg.lower() or "auth" in error_msg.lower():
            return {
                "success": False,
                "error": "Calendar authentication issue. You may need to re-authenticate with Google.",
                "error_type": "auth_error"
            }
        elif "not found" in error_msg.lower():
            return {
                "success": False,
                "error": f"Could not find the requested resource: {error_msg}",
                "error_type": "not_found"
            }
        else:
            return {
                "success": False,
                "error": f"Error: {error_msg}",
                "error_type": "unknown"
            }
