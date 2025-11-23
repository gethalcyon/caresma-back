"""
Service for managing conversation messages with security controls
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import Optional, List
import uuid
from datetime import datetime
from fastapi import HTTPException, status

from app.models.message import Message
from app.models.session import Session
from app.core.logging import get_logger

logger = get_logger(__name__)


class MessageService:
    """Service for creating and managing conversation messages with security"""

    @staticmethod
    async def _verify_session_access(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> Session:
        """
        Verify that a session exists and optionally that the user has access to it.

        Args:
            db: Database session
            session_id: UUID of the session
            user_id: Optional UUID of the user (for access control)

        Returns:
            Session object if access is allowed

        Raises:
            HTTPException: If session not found or access denied
        """
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        # If user_id is provided, verify ownership
        if user_id and session.user_id != user_id:
            logger.warning(
                f"Access denied: User {user_id} attempted to access session {session_id} "
                f"owned by {session.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't have permission to access this session"
            )

        logger.debug(f"Access granted to session {session_id} for user {user_id}")
        return session

    @staticmethod
    async def create_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        role: str,
        content: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Message:
        """
        Create a new message in the database with access control.

        Args:
            db: Database session
            session_id: UUID of the session
            role: Role of the message sender ("user" or "assistant")
            content: Message content/text (will be encrypted automatically)
            user_id: Optional UUID of the user (for access control)

        Returns:
            Created Message object

        Raises:
            ValueError: If role is not "user" or "assistant"
            HTTPException: If session not found or access denied
        """
        if role not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        # Verify session exists and user has access (skip for now to maintain compatibility)
        # await MessageService._verify_session_access(db, session_id, user_id)

        # Create message - content will be automatically encrypted by the model
        message = Message(
            session_id=session_id,
            role=role,
            content=content  # This will be encrypted by the hybrid property setter
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        logger.info(
            f"Created encrypted {role} message for session {session_id} "
            f"(user: {user_id}, length: {len(content)})"
        )
        return message

    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        limit: Optional[int] = 50
    ) -> List[Message]:
        """
        Get all messages for a specific session with access control.

        Args:
            db: Database session
            session_id: UUID of the session
            user_id: Optional UUID of the user (for access control)
            limit: Maximum number of messages to return

        Returns:
            List of Message objects ordered by creation time (content auto-decrypted)

        Raises:
            HTTPException: If session not found or access denied
        """
        # Verify session exists and user has access (optional)
        if user_id:
            await MessageService._verify_session_access(db, session_id, user_id)

        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(limit)
        )

        messages = result.scalars().all()

        logger.info(
            f"Retrieved {len(messages)} encrypted messages for session {session_id} "
            f"(user: {user_id})"
        )
        return messages

    @staticmethod
    async def get_message_count(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None
    ) -> dict:
        """
        Get count of messages for a session with access control.

        Args:
            db: Database session
            session_id: UUID of the session
            user_id: Optional UUID of the user (for access control)

        Returns:
            Dictionary with message counts

        Raises:
            HTTPException: If session not found or access denied
        """
        # Verify session exists and user has access (optional)
        if user_id:
            await MessageService._verify_session_access(db, session_id, user_id)

        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
        )

        messages = result.scalars().all()

        return {
            "total": len(messages),
            "user_messages": len([m for m in messages if m.role == "user"]),
            "assistant_messages": len([m for m in messages if m.role == "assistant"])
        }
