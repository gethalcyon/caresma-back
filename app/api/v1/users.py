from fastapi import APIRouter

from app.core.users import fastapi_users
from app.schemas.user import UserRead, UserUpdate

# Get user routers from fastapi-users
router = APIRouter(prefix="/users", tags=["users"])

# Include fastapi-users user routers
# This provides: /me (GET, PATCH), /{id} (GET, PATCH, DELETE)
users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
router.include_router(users_router)
