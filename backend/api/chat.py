"""Chat API endpoints."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..services.memory_service import MemoryService
from ..services.ai_orchestrator import AIOrchestrator
from ..models.schemas import (
    ChatMessage,
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.websocket("/ws/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    orchestrator = AIOrchestrator(db)
    memory_service = MemoryService(db)

    # Verify conversation exists
    conversation = memory_service.get_conversation(conversation_id)
    if not conversation:
        await websocket.send_json({"type": "error", "message": "Conversation not found"})
        await websocket.close()
        return

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            # Process message and stream response
            async for chunk in orchestrator.process_message(user_message, conversation_id):
                await websocket.send_json(chunk)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()


@router.post("/message")
async def send_message(
    chat_message: ChatMessage,
    db: Session = Depends(get_db),
):
    """Send a message (non-streaming fallback)."""
    memory_service = MemoryService(db)
    orchestrator = AIOrchestrator(db)

    # Create conversation if needed
    conversation_id = chat_message.conversation_id
    if not conversation_id:
        conversation = memory_service.create_conversation()
        conversation_id = conversation.id

    # Process message
    result = orchestrator.process_message_sync(
        user_message=chat_message.message,
        conversation_id=conversation_id,
    )

    return {
        "conversation_id": conversation_id,
        "response": result["content"],
        "function_results": result.get("function_results", []),
    }


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
):
    """Create a new conversation."""
    memory_service = MemoryService(db)
    return memory_service.create_conversation(title=conversation.title)


@router.get("/conversations", response_model=list[ConversationListResponse])
def list_conversations(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List recent conversations."""
    memory_service = MemoryService(db)
    conversations = memory_service.get_recent_conversations(limit=limit)

    return [
        ConversationListResponse(
            id=c.id,
            title=c.title,
            summary=c.summary,
            started_at=c.started_at,
            updated_at=c.updated_at,
            message_count=len(c.messages),
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Get a conversation with messages."""
    memory_service = MemoryService(db)
    conversation = memory_service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """Delete a conversation."""
    memory_service = MemoryService(db)
    success = memory_service.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"success": True}


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get messages for a conversation."""
    memory_service = MemoryService(db)
    return memory_service.get_conversation_messages(conversation_id, limit=limit)
