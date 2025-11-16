from fastapi import APIRouter
from app.api.v1 import auth, users, sessions, websocket

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sessions.router)
api_router.include_router(websocket.router)
