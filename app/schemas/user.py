from fastapi_users import schemas
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserRead(schemas.BaseUser[UUID]):
    """Schema for reading user data"""

    full_name: Optional[str] = None
    created_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a user"""

    full_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating a user"""

    full_name: Optional[str] = None
