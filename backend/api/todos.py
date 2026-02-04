"""Todo list API endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.database import TodoItem
from ..models.schemas import TodoItemCreate, TodoItemUpdate, TodoItemResponse

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("/", response_model=List[TodoItemResponse])
def get_todos(
    completed: bool = None,
    priority: str = None,
    db: Session = Depends(get_db),
):
    """Get all todos, optionally filtered by status or priority."""
    query = db.query(TodoItem)
    
    if completed is not None:
        query = query.filter(TodoItem.completed == completed)
    if priority:
        query = query.filter(TodoItem.priority == priority)
    
    # Order by: incomplete first, then by priority (high > medium > low), then by due date
    priority_order = {"high": 1, "medium": 2, "low": 3}
    todos = query.all()
    
    # Sort in Python for flexibility
    def sort_key(t):
        priority_val = priority_order.get(t.priority, 2)
        due_val = t.due_date if t.due_date else datetime.max
        return (t.completed, priority_val, due_val)
    
    return sorted(todos, key=sort_key)


@router.post("/", response_model=TodoItemResponse)
def create_todo(todo: TodoItemCreate, db: Session = Depends(get_db)):
    """Create a new todo item."""
    db_todo = TodoItem(
        title=todo.title,
        description=todo.description,
        priority=todo.priority,
        due_date=todo.due_date,
        estimated_minutes=todo.estimated_minutes,
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo


@router.get("/{todo_id}", response_model=TodoItemResponse)
def get_todo(todo_id: int, db: Session = Depends(get_db)):
    """Get a specific todo item."""
    todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/{todo_id}", response_model=TodoItemResponse)
def update_todo(todo_id: int, updates: TodoItemUpdate, db: Session = Depends(get_db)):
    """Update a todo item."""
    todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    update_data = updates.model_dump(exclude_unset=True)
    
    # If marking as completed, set completed_at
    if "completed" in update_data:
        if update_data["completed"] and not todo.completed:
            update_data["completed_at"] = datetime.utcnow()
        elif not update_data["completed"]:
            update_data["completed_at"] = None
    
    for key, value in update_data.items():
        setattr(todo, key, value)
    
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    """Delete a todo item."""
    todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    db.delete(todo)
    db.commit()
    return {"status": "deleted", "id": todo_id}


@router.post("/{todo_id}/toggle", response_model=TodoItemResponse)
def toggle_todo(todo_id: int, db: Session = Depends(get_db)):
    """Toggle a todo's completed status."""
    todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    todo.completed = not todo.completed
    todo.completed_at = datetime.utcnow() if todo.completed else None
    
    db.commit()
    db.refresh(todo)
    return todo
