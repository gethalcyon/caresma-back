from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming.

    Args:
        websocket: WebSocket connection
        session_id: Session ID for this conversation
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session: {session_id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.debug(f"Received message from session {session_id}: {data}")

            # Echo the message back (for testing)
            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for session {session_id}: {e}")
        await websocket.close()
