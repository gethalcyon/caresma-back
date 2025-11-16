import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger
from app.services.openai_service import get_openai_service

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

    # Get OpenAI service instance
    openai_service = get_openai_service()

    # Connect to OpenAI Realtime API
    connected = await openai_service.connect()
    if not connected:
        logger.error(f"Failed to connect to OpenAI for session {session_id}")
        await websocket.send_json({"error": "Failed to connect to AI service"})
        await websocket.close()
        return

    # Start conversation
    conversation_started = await openai_service.start_conversation(
        system_prompt="You are a helpful cognitive health assistant for elderly users. "
                     "Be warm, patient, and encouraging. Ask questions to assess memory, "
                     "language skills, and attention.",
        voice="alloy"
    )

    if not conversation_started:
        logger.error(f"Failed to start conversation for session {session_id}")
        await websocket.send_json({"error": "Failed to start conversation"})
        await websocket.close()
        return

    logger.info(f"OpenAI conversation started for session: {session_id}")

    try:
        while True:
            # Receive data from client (can be text or binary)
            message = await websocket.receive()

            # Handle text messages (control messages)
            if "text" in message:
                data = json.loads(message["text"])
                logger.debug(f"Received text message from session {session_id}: {data}")

                # Handle different message types
                msg_type = data.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "start_recording":
                    logger.info(f"Session {session_id} started recording")
                    await websocket.send_json({"type": "recording_started"})

                elif msg_type == "stop_recording":
                    logger.info(f"Session {session_id} stopped recording")
                    await websocket.send_json({"type": "recording_stopped"})

            # Handle binary messages (audio data)
            elif "bytes" in message:
                audio_data = message["bytes"]
                logger.debug(f"Received {len(audio_data)} bytes of audio from session {session_id}")

                # Forward audio to OpenAI
                success = await openai_service.send_audio(audio_data)

                if not success:
                    logger.warning(f"Failed to send audio to OpenAI for session {session_id}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to process audio"
                    })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
        await openai_service.disconnect()

    except Exception as e:
        logger.error(f"Error in WebSocket connection for session {session_id}: {e}")
        await openai_service.disconnect()
        # Only close if not already disconnected
        try:
            await websocket.close()
        except RuntimeError:
            pass  # WebSocket already closed
