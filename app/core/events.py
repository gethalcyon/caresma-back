from fastapi import FastAPI
from app.core.logging import setup_logging, get_logger
from app.db.session import engine
from app.db.base import Base

logger = get_logger(__name__)


async def startup_event(app: FastAPI):
    """Application startup event handler"""
    logger.info("Starting up Caresma Backend...")
    setup_logging()

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")
    logger.info("Application startup complete")


async def shutdown_event(app: FastAPI):
    """Application shutdown event handler"""
    logger.info("Shutting down Caresma Backend...")
    await engine.dispose()
    logger.info("Application shutdown complete")
