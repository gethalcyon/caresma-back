from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List

from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse


class SessionService:
    """Service layer for session business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = SessionRepository()

    async def create_session(self, user_id: UUID, session_data: SessionCreate) -> SessionResponse:
        """Create a new session"""
        session = await self.repository.create(self.db, user_id, session_data)
        return SessionResponse.model_validate(session)

    async def get_session(self, session_id: UUID, user_id: UUID) -> SessionResponse:
        """Get session by ID"""
        session = await self.repository.get_by_id(self.db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify the session belongs to the user
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session",
            )

        return SessionResponse.model_validate(session)

    async def get_user_sessions(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[SessionResponse]:
        """Get all sessions for a user"""
        sessions = await self.repository.get_user_sessions(self.db, user_id, skip, limit)
        return [SessionResponse.model_validate(session) for session in sessions]

    async def update_session(
        self, session_id: UUID, user_id: UUID, session_data: SessionUpdate
    ) -> SessionResponse:
        """Update session"""
        session = await self.repository.get_by_id(self.db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify the session belongs to the user
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this session",
            )

        updated_session = await self.repository.update(self.db, session, session_data)
        return SessionResponse.model_validate(updated_session)

    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        """Delete session"""
        session = await self.repository.get_by_id(self.db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify the session belongs to the user
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this session",
            )

        await self.repository.delete(self.db, session)

    async def end_session(self, session_id: UUID, user_id: UUID) -> SessionResponse:
        """End a session"""
        session = await self.repository.get_by_id(self.db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify the session belongs to the user
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this session",
            )

        ended_session = await self.repository.end_session(self.db, session)
        return SessionResponse.model_validate(ended_session)
