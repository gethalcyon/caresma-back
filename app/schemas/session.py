from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class SessionBase(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    ended_at: Optional[datetime] = None


class SessionInDB(SessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class SessionResponse(SessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
