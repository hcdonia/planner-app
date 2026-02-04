"""Knowledge API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..services.knowledge_service import KnowledgeService
from ..models.schemas import (
    KnowledgeCreate,
    KnowledgeUpdate,
    KnowledgeResponse,
    AIInstructionCreate,
    AIInstructionUpdate,
    AIInstructionResponse,
    SchedulingRuleCreate,
    SchedulingRuleUpdate,
    SchedulingRuleResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ============ Knowledge Endpoints ============

@router.get("/", response_model=list[KnowledgeResponse])
def list_knowledge(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all knowledge entries."""
    knowledge_service = KnowledgeService(db)
    if category:
        return knowledge_service.get_knowledge_by_category(category)
    return knowledge_service.get_all_knowledge()


@router.post("/", response_model=KnowledgeResponse)
def create_knowledge(
    knowledge: KnowledgeCreate,
    db: Session = Depends(get_db),
):
    """Create a new knowledge entry."""
    knowledge_service = KnowledgeService(db)
    return knowledge_service.save_knowledge(
        category=knowledge.category,
        subject=knowledge.subject,
        content=knowledge.content,
        source=knowledge.source,
        confidence=knowledge.confidence,
    )


@router.get("/search")
def search_knowledge(
    query: str,
    db: Session = Depends(get_db),
):
    """Search knowledge entries."""
    knowledge_service = KnowledgeService(db)
    results = knowledge_service.get_knowledge(query)
    return {"results": [KnowledgeResponse.model_validate(k) for k in results]}


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
def update_knowledge(
    knowledge_id: int,
    updates: KnowledgeUpdate,
    db: Session = Depends(get_db),
):
    """Update a knowledge entry."""
    knowledge_service = KnowledgeService(db)

    # Get current knowledge
    current = knowledge_service.get_knowledge(str(knowledge_id))
    if not current:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    if updates.content:
        result = knowledge_service.update_knowledge(knowledge_id, updates.content)
        if result:
            return result

    raise HTTPException(status_code=404, detail="Knowledge not found")


@router.delete("/{knowledge_id}")
def delete_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
):
    """Delete a knowledge entry."""
    knowledge_service = KnowledgeService(db)
    success = knowledge_service.delete_knowledge(knowledge_id)
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return {"success": True}


# ============ Instruction Endpoints ============

@router.get("/instructions", response_model=list[AIInstructionResponse])
def list_instructions(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all AI instructions."""
    knowledge_service = KnowledgeService(db)
    if category:
        return knowledge_service.get_instructions_by_category(category)
    return knowledge_service.get_all_instructions()


@router.post("/instructions", response_model=AIInstructionResponse)
def create_instruction(
    instruction: AIInstructionCreate,
    db: Session = Depends(get_db),
):
    """Create a new AI instruction."""
    knowledge_service = KnowledgeService(db)
    return knowledge_service.add_instruction(
        category=instruction.category,
        instruction=instruction.instruction,
        source=instruction.source,
    )


@router.put("/instructions/{instruction_id}", response_model=AIInstructionResponse)
def update_instruction(
    instruction_id: int,
    updates: AIInstructionUpdate,
    db: Session = Depends(get_db),
):
    """Update an AI instruction."""
    knowledge_service = KnowledgeService(db)
    if updates.instruction:
        result = knowledge_service.update_instruction(instruction_id, updates.instruction)
        if result:
            return result
    raise HTTPException(status_code=404, detail="Instruction not found")


@router.delete("/instructions/{instruction_id}")
def delete_instruction(
    instruction_id: int,
    db: Session = Depends(get_db),
):
    """Delete an AI instruction."""
    knowledge_service = KnowledgeService(db)
    success = knowledge_service.delete_instruction(instruction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return {"success": True}


# ============ Scheduling Rule Endpoints ============

@router.get("/rules", response_model=list[SchedulingRuleResponse])
def list_rules(
    rule_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all scheduling rules."""
    knowledge_service = KnowledgeService(db)
    if rule_type:
        return knowledge_service.get_rules_by_type(rule_type)
    return knowledge_service.get_all_rules()


@router.post("/rules", response_model=SchedulingRuleResponse)
def create_rule(
    rule: SchedulingRuleCreate,
    db: Session = Depends(get_db),
):
    """Create a new scheduling rule."""
    knowledge_service = KnowledgeService(db)
    return knowledge_service.add_scheduling_rule(
        rule_type=rule.rule_type,
        name=rule.name,
        config=rule.config,
    )


@router.put("/rules/{rule_id}", response_model=SchedulingRuleResponse)
def update_rule(
    rule_id: int,
    updates: SchedulingRuleUpdate,
    db: Session = Depends(get_db),
):
    """Update a scheduling rule."""
    knowledge_service = KnowledgeService(db)
    if updates.config:
        result = knowledge_service.update_rule(rule_id, updates.config)
        if result:
            return result
    raise HTTPException(status_code=404, detail="Rule not found")


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
):
    """Delete a scheduling rule."""
    knowledge_service = KnowledgeService(db)
    success = knowledge_service.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}
