"""
API endpoints for retrieving conversation messages
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.db.session import get_db
from app.db.message import Message

router = APIRouter()


class MessageResponse(BaseModel):
    """Response model for a message"""
    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
async def get_thread_messages(
    thread_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all messages for a specific thread (session).

    Args:
        thread_id: UUID of the thread/session
        limit: Maximum number of messages to return (default: 50)
        db: Database session

    Returns:
        List of messages ordered by creation time (oldest first)
    """
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread ID format"
        )

    # Query messages for this thread
    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_uuid)
        .order_by(Message.created_at)  # Chronological order
        .limit(limit)
    )

    messages = result.scalars().all()

    return [
        MessageResponse(
            id=str(msg.id),
            thread_id=str(msg.thread_id),
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at
        )
        for msg in messages
    ]


@router.get("/threads/{thread_id}/messages/count")
async def get_thread_message_count(
    thread_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the count of messages for a specific thread.

    Args:
        thread_id: UUID of the thread/session
        db: Database session

    Returns:
        Count of messages in the thread
    """
    try:
        thread_uuid = uuid.UUID(thread_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread ID format"
        )

    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_uuid)
    )

    messages = result.scalars().all()

    return {
        "thread_id": thread_id,
        "message_count": len(messages),
        "user_messages": len([m for m in messages if m.role == "user"]),
        "assistant_messages": len([m for m in messages if m.role == "assistant"])
    }
