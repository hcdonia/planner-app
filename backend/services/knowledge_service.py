"""Knowledge service - manages knowledge entries."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models.database import Knowledge, AIInstruction, SchedulingRule, Calendar


class KnowledgeService:
    """Service for managing knowledge, instructions, and rules."""

    def __init__(self, db: Session):
        self.db = db

    # ============ Knowledge Operations ============

    def save_knowledge(
        self,
        category: str,
        subject: str,
        content: str,
        source: str = "conversation",
        confidence: float = 1.0,
    ) -> Knowledge:
        """Save a new knowledge entry or update existing one."""
        # Check if we already have knowledge about this subject
        existing = (
            self.db.query(Knowledge)
            .filter(Knowledge.subject.ilike(f"%{subject}%"))
            .filter(Knowledge.category == category)
            .first()
        )

        if existing:
            existing.content = content
            existing.source = source
            existing.confidence = confidence
            self.db.commit()
            self.db.refresh(existing)
            return existing

        knowledge = Knowledge(
            category=category,
            subject=subject,
            content=content,
            source=source,
            confidence=confidence,
        )
        self.db.add(knowledge)
        self.db.commit()
        self.db.refresh(knowledge)
        return knowledge

    def get_knowledge(self, query: str) -> List[Knowledge]:
        """Search for knowledge entries matching a query."""
        return (
            self.db.query(Knowledge)
            .filter(Knowledge.active == True)
            .filter(
                or_(
                    Knowledge.subject.ilike(f"%{query}%"),
                    Knowledge.content.ilike(f"%{query}%"),
                    Knowledge.category.ilike(f"%{query}%"),
                )
            )
            .all()
        )

    def get_all_knowledge(self) -> List[Knowledge]:
        """Get all active knowledge entries."""
        return self.db.query(Knowledge).filter(Knowledge.active == True).all()

    def get_knowledge_by_category(self, category: str) -> List[Knowledge]:
        """Get all knowledge entries for a category."""
        return (
            self.db.query(Knowledge)
            .filter(Knowledge.active == True)
            .filter(Knowledge.category == category)
            .all()
        )

    def update_knowledge(self, knowledge_id: int, content: str) -> Optional[Knowledge]:
        """Update an existing knowledge entry."""
        knowledge = self.db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if knowledge:
            knowledge.content = content
            self.db.commit()
            self.db.refresh(knowledge)
        return knowledge

    def delete_knowledge(self, knowledge_id: int) -> bool:
        """Soft delete a knowledge entry."""
        knowledge = self.db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if knowledge:
            knowledge.active = False
            self.db.commit()
            return True
        return False

    # ============ AI Instruction Operations ============

    def add_instruction(
        self,
        category: str,
        instruction: str,
        source: str = "user",
    ) -> AIInstruction:
        """Add a new AI instruction."""
        inst = AIInstruction(
            category=category,
            instruction=instruction,
            source=source,
        )
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return inst

    def get_all_instructions(self) -> List[AIInstruction]:
        """Get all active AI instructions."""
        return self.db.query(AIInstruction).filter(AIInstruction.active == True).all()

    def get_instructions_by_category(self, category: str) -> List[AIInstruction]:
        """Get all instructions for a category."""
        return (
            self.db.query(AIInstruction)
            .filter(AIInstruction.active == True)
            .filter(AIInstruction.category == category)
            .all()
        )

    def update_instruction(
        self,
        instruction_id: int,
        new_instruction: str,
    ) -> Optional[AIInstruction]:
        """Update an existing instruction."""
        inst = self.db.query(AIInstruction).filter(AIInstruction.id == instruction_id).first()
        if inst:
            inst.instruction = new_instruction
            self.db.commit()
            self.db.refresh(inst)
        return inst

    def delete_instruction(self, instruction_id: int) -> bool:
        """Soft delete an instruction."""
        inst = self.db.query(AIInstruction).filter(AIInstruction.id == instruction_id).first()
        if inst:
            inst.active = False
            self.db.commit()
            return True
        return False

    # ============ Scheduling Rule Operations ============

    def add_scheduling_rule(
        self,
        rule_type: str,
        name: str,
        config: dict,
    ) -> SchedulingRule:
        """Add a new scheduling rule."""
        rule = SchedulingRule(
            rule_type=rule_type,
            name=name,
            config=config,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_all_rules(self) -> List[SchedulingRule]:
        """Get all active scheduling rules."""
        return self.db.query(SchedulingRule).filter(SchedulingRule.active == True).all()

    def get_rules_by_type(self, rule_type: str) -> List[SchedulingRule]:
        """Get all rules of a specific type."""
        return (
            self.db.query(SchedulingRule)
            .filter(SchedulingRule.active == True)
            .filter(SchedulingRule.rule_type == rule_type)
            .all()
        )

    def update_rule(self, rule_id: int, config: dict) -> Optional[SchedulingRule]:
        """Update a scheduling rule's config."""
        rule = self.db.query(SchedulingRule).filter(SchedulingRule.id == rule_id).first()
        if rule:
            rule.config = config
            self.db.commit()
            self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """Soft delete a scheduling rule."""
        rule = self.db.query(SchedulingRule).filter(SchedulingRule.id == rule_id).first()
        if rule:
            rule.active = False
            self.db.commit()
            return True
        return False

    # ============ Calendar Operations ============

    def add_calendar(
        self,
        name: str,
        google_calendar_id: str,
        permission: str = "read",
        color: Optional[str] = None,
        priority: int = 5,
    ) -> Calendar:
        """Add a new calendar to track."""
        calendar = Calendar(
            name=name,
            google_calendar_id=google_calendar_id,
            permission=permission,
            color=color,
            priority=priority,
        )
        self.db.add(calendar)
        self.db.commit()
        self.db.refresh(calendar)
        return calendar

    def get_all_calendars(self) -> List[Calendar]:
        """Get all active calendars."""
        return self.db.query(Calendar).filter(Calendar.active == True).all()

    def update_calendar(self, calendar_id: int, updates: dict) -> Optional[Calendar]:
        """Update a calendar's settings."""
        calendar = self.db.query(Calendar).filter(Calendar.id == calendar_id).first()
        if calendar:
            for key, value in updates.items():
                if hasattr(calendar, key):
                    setattr(calendar, key, value)
            self.db.commit()
            self.db.refresh(calendar)
        return calendar

    def remove_calendar(self, calendar_id: int) -> bool:
        """Soft delete a calendar."""
        calendar = self.db.query(Calendar).filter(Calendar.id == calendar_id).first()
        if calendar:
            calendar.active = False
            self.db.commit()
            return True
        return False

    def get_calendar_by_name(self, name: str) -> Optional[Calendar]:
        """Get a calendar by name."""
        return (
            self.db.query(Calendar)
            .filter(Calendar.active == True)
            .filter(Calendar.name.ilike(f"%{name}%"))
            .first()
        )
