from fastapi import APIRouter

from app.core.users import auth_backend, fastapi_users
from app.schemas.user import UserRead, UserCreate

# Create auth router with fastapi-users
auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)

# Combine routers
router = APIRouter(prefix="/auth", tags=["authentication"])
router.include_router(auth_router)
router.include_router(register_router)
