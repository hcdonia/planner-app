"""Context builder - builds dynamic prompts for the AI."""
import datetime as dt
import json
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.database import Calendar, AIInstruction, Knowledge, SchedulingRule
from .calendar_service import CalendarService
from .knowledge_service import KnowledgeService
from .memory_service import MemoryService

settings = get_settings()


class ContextBuilder:
    """Builds dynamic system prompts and context for the AI."""

    def __init__(self, db: Session):
        self.db = db
        self.calendar_service = CalendarService(db)
        self.knowledge_service = KnowledgeService(db)
        self.memory_service = MemoryService(db)

    def build_system_prompt(self) -> str:
        """Build the complete system prompt from database."""
        parts = [self._get_base_prompt()]

        # Add current context
        parts.append(self._build_time_context())

        # Add instructions from database
        instructions = self._build_instructions_context()
        if instructions:
            parts.append(instructions)

        # Add knowledge
        knowledge = self._build_knowledge_context()
        if knowledge:
            parts.append(knowledge)

        # Add calendars
        calendars = self._build_calendar_context()
        if calendars:
            parts.append(calendars)

        # Add scheduling rules
        rules = self._build_rules_context()
        if rules:
            parts.append(rules)

        # Add today's schedule
        schedule = self._build_today_schedule()
        if schedule:
            parts.append(schedule)

        # Add function instructions
        parts.append(self._get_function_instructions())

        return "\n\n".join(parts)

    def _get_base_prompt(self) -> str:
        """Get the minimal base prompt."""
        return """You are an intelligent planning assistant. You help schedule tasks, manage calendars, and learn about the user to become more helpful over time.

## Core Capabilities
- Schedule tasks and events on the user's calendars
- Check calendar availability across multiple calendars
- Remember and learn from conversations
- Store knowledge about the user, their business, and preferences
- Modify your own instructions and behavior based on user feedback
- Add, update, or remove calendars dynamically

## Personality
- Be conversational but efficient
- Ask clarifying questions when needed
- Proactively ask for context that would help you assist better
- Learn and adapt to the user's preferences
- Be direct and helpful"""

    def _build_time_context(self) -> str:
        """Build current time context."""
        tz = ZoneInfo(settings.TIMEZONE)
        now = dt.datetime.now(tz)

        return f"""## Current Context
- Current time: {now.strftime("%I:%M %p")}
- Today: {now.strftime("%A, %B %d, %Y")}
- Timezone: {settings.TIMEZONE}"""

    def _build_instructions_context(self) -> str:
        """Build instructions section from database."""
        instructions = self.db.query(AIInstruction).filter(AIInstruction.active == True).all()

        if not instructions:
            return ""

        # Group by category
        by_category: Dict[str, List[str]] = {}
        for inst in instructions:
            if inst.category not in by_category:
                by_category[inst.category] = []
            by_category[inst.category].append(inst.instruction)

        parts = ["## Custom Instructions"]
        for category, insts in by_category.items():
            parts.append(f"\n### {category.title()}")
            for inst in insts:
                parts.append(f"- {inst}")

        return "\n".join(parts)

    def _build_knowledge_context(self) -> str:
        """Build knowledge section from database."""
        knowledge = self.db.query(Knowledge).filter(Knowledge.active == True).all()

        if not knowledge:
            return ""

        # Group by category
        by_category: Dict[str, List[Knowledge]] = {}
        for k in knowledge:
            if k.category not in by_category:
                by_category[k.category] = []
            by_category[k.category].append(k)

        parts = ["## What I Know About You"]
        for category, items in by_category.items():
            parts.append(f"\n### {category.title()}")
            for item in items:
                parts.append(f"- **{item.subject}**: {item.content}")

        return "\n".join(parts)

    def _build_calendar_context(self) -> str:
        """Build calendar configuration section."""
        calendars = self.db.query(Calendar).filter(Calendar.active == True).all()

        if not calendars:
            return """## Calendars
No calendars configured yet. Ask the user which calendars they want to track."""

        parts = ["## Calendars I Have Access To"]
        for cal in calendars:
            perm = "read & write" if cal.permission == "read_write" else "read only"
            parts.append(f"- **{cal.name}** ({perm})")

        return "\n".join(parts)

    def _build_rules_context(self) -> str:
        """Build scheduling rules section."""
        rules = self.db.query(SchedulingRule).filter(SchedulingRule.active == True).all()

        if not rules:
            return ""

        parts = ["## Scheduling Rules"]
        for rule in rules:
            config_str = json.dumps(rule.config, indent=2)
            parts.append(f"- **{rule.name}** ({rule.rule_type}): {config_str}")

        return "\n".join(parts)

    def _build_today_schedule(self) -> str:
        """Build today's schedule summary."""
        try:
            tz = ZoneInfo(settings.TIMEZONE)
            today = dt.datetime.now(tz).date()
            events = self.calendar_service.get_day_schedule(today)

            if not events:
                return "## Today's Schedule\nNo events scheduled for today."

            parts = ["## Today's Schedule"]
            parts.append(self.calendar_service.format_schedule_summary(events))
            return "\n".join(parts)
        except Exception:
            # Calendar might not be set up yet
            return ""

    def _get_function_instructions(self) -> str:
        """Get instructions for using functions."""
        return """## How to Use Your Functions

### Calendar Operations
- Use `check_availability` to find free time slots
- Use `schedule_task` to create events (always confirm with user first)
- Use `get_day_schedule` or `get_week_overview` for schedule context
- Use `reschedule_task` to move existing events

### Self-Modification
- Use `save_knowledge` when you learn something important about the user
- Use `add_instruction` when the user tells you how to behave
- Use `add_scheduling_rule` for scheduling preferences
- Use `add_calendar` when the user wants to track a new calendar

### Important Guidelines
1. Always confirm before creating or modifying calendar events
2. Save important context using save_knowledge
3. When the user gives you instructions about behavior, save them with add_instruction
4. Ask for clarification when the user's request is ambiguous
5. Proactively ask for context that would help you assist better"""

    def build_messages_for_ai(
        self,
        conversation_id: int,
        user_message: str,
        max_history: int = 20,
    ) -> List[Dict[str, str]]:
        """Build the complete messages array for OpenAI API."""
        messages = []

        # System prompt
        messages.append({
            "role": "system",
            "content": self.build_system_prompt(),
        })

        # Conversation history
        history = self.memory_service.get_recent_messages(conversation_id, limit=max_history)
        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Current user message
        messages.append({
            "role": "user",
            "content": user_message,
        })

        return messages

    def get_calendar_context_for_scheduling(
        self,
        days_ahead: int = 7,
    ) -> str:
        """Get detailed calendar context for scheduling decisions."""
        try:
            tz = ZoneInfo(settings.TIMEZONE)
            now = dt.datetime.now(tz)
            today = now.date()

            parts = ["Current schedule context:"]

            # Today
            today_events = self.calendar_service.get_day_schedule(today)
            parts.append(f"\n**Today ({today.strftime('%A')}):**")
            if today_events:
                remaining = [e for e in today_events if e["start"] > now]
                if remaining:
                    parts.append(self.calendar_service.format_schedule_summary(remaining))
                else:
                    parts.append("No more events today.")
            else:
                parts.append("Clear day.")

            # Next few days
            for i in range(1, min(days_ahead + 1, 4)):
                day = today + dt.timedelta(days=i)
                events = self.calendar_service.get_day_schedule(day)
                parts.append(f"\n**{day.strftime('%A, %b %d')}:**")
                if events:
                    parts.append(self.calendar_service.format_schedule_summary(events))
                else:
                    parts.append("Clear day.")

            return "\n".join(parts)
        except Exception as e:
            return f"(Could not fetch schedule: {e})"
