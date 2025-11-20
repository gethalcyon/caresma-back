"""
Service for managing conversation messages
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import uuid
from datetime import datetime

from app.db.message import Message
from app.core.logging import get_logger

logger = get_logger(__name__)


class MessageService:
    """Service for creating and managing conversation messages"""

    @staticmethod
    async def create_message(
        db: AsyncSession,
        thread_id: uuid.UUID,
        role: str,
        content: str
    ) -> Message:
        """
        Create a new message in the database.

        Args:
            db: Database session
            thread_id: UUID of the session/thread
            role: Role of the message sender ("user" or "assistant")
            content: Message content/text

        Returns:
            Created Message object

        Raises:
            ValueError: If role is not "user" or "assistant"
        """
        if role not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        message = Message(
            thread_id=thread_id,
            role=role,
            content=content
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        logger.info(f"Created {role} message for thread {thread_id}: {content[:50]}...")
        return message

    @staticmethod
    async def get_thread_messages(
        db: AsyncSession,
        thread_id: uuid.UUID,
        limit: Optional[int] = 50
    ) -> List[Message]:
        """
        Get all messages for a specific thread.

        Args:
            db: Database session
            thread_id: UUID of the session/thread
            limit: Maximum number of messages to return

        Returns:
            List of Message objects ordered by creation time
        """
        result = await db.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at)
            .limit(limit)
        )

        messages = result.scalars().all()
        return messages

    @staticmethod
    async def get_message_count(
        db: AsyncSession,
        thread_id: uuid.UUID
    ) -> dict:
        """
        Get count of messages for a thread.

        Args:
            db: Database session
            thread_id: UUID of the session/thread

        Returns:
            Dictionary with message counts
        """
        result = await db.execute(
            select(Message)
            .where(Message.thread_id == thread_id)
        )

        messages = result.scalars().all()

        return {
            "total": len(messages),
            "user_messages": len([m for m in messages if m.role == "user"]),
            "assistant_messages": len([m for m in messages if m.role == "assistant"])
        }
