from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.session import Session
from app.schemas.session import SessionCreate, SessionUpdate


class SessionRepository:
    """Repository for Session database operations"""

    @staticmethod
    async def create(db: AsyncSession, user_id: UUID, session_data: SessionCreate) -> Session:
        """Create a new session"""
        session = Session(
            user_id=user_id,
            title=session_data.title,
            metadata=session_data.metadata,
            notes=session_data.notes,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_by_id(db: AsyncSession, session_id: UUID) -> Optional[Session]:
        """Get session by ID"""
        result = await db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_sessions(
        db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Session]:
        """Get all sessions for a user"""
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Session.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update(db: AsyncSession, session: Session, session_data: SessionUpdate) -> Session:
        """Update session"""
        update_data = session_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(session, field, value)

        await db.flush()
        await db.refresh(session)
        return session

    @staticmethod
    async def delete(db: AsyncSession, session: Session) -> None:
        """Delete session"""
        await db.delete(session)
        await db.flush()

    @staticmethod
    async def end_session(db: AsyncSession, session: Session) -> Session:
        """End a session"""
        session.status = "completed"
        session.ended_at = datetime.utcnow()
        await db.flush()
        await db.refresh(session)
        return session
