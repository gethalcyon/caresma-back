from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse
from app.services.session_service import SessionService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new session"""
    session_service = SessionService(db)
    return await session_service.create_session(current_user.id, session_data)


@router.get("", response_model=List[SessionResponse])
async def get_user_sessions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all sessions for current user"""
    session_service = SessionService(db)
    return await session_service.get_user_sessions(current_user.id, skip, limit)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get session by ID"""
    session_service = SessionService(db)
    return await session_service.get_session(session_id, current_user.id)


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
    session_data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update session"""
    session_service = SessionService(db)
    return await session_service.update_session(session_id, current_user.id, session_data)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete session"""
    session_service = SessionService(db)
    await session_service.delete_session(session_id, current_user.id)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a session"""
    session_service = SessionService(db)
    return await session_service.end_session(session_id, current_user.id)
