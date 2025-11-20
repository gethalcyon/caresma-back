import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger
from app.services.openai_service import get_openai_service
from app.services.Messages import MessageService
from app.db.session import get_db

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming with OpenAI.

    New Architecture:
    - Backend: OpenAI Realtime API (ASR + LLM) → sends text responses to frontend
    - Frontend: @heygen/streaming-avatar SDK → handles avatar video/TTS

    Flow:
    1. User speaks → audio → backend
    2. OpenAI ASR → text transcript
    3. OpenAI LLM → text response
    4. Backend sends text response → frontend
    5. Frontend avatar.speak(text) → HeyGen renders avatar video

    Args:
        websocket: WebSocket connection
        session_id: Session ID for this conversation
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session: {session_id}")

    # Get OpenAI service
    openai_service = get_openai_service()

    # Connect to OpenAI Realtime API
    connected = await openai_service.connect()
    if not connected:
        logger.error(f"Failed to connect to OpenAI for session {session_id}")
        await websocket.send_json({"error": "Failed to connect to AI service"})
        await websocket.close()
        return

    # Start conversation in text-only mode
    # OpenAI will handle ASR (audio → text) and LLM (text → text)
    # Frontend will handle TTS via HeyGen avatar
    conversation_started = await openai_service.start_conversation(
        system_prompt="You are a helpful cognitive health assistant for elderly users. "
                     "Be warm, patient, and encouraging. Ask questions to assess memory, "
                     "language skills, and attention.",
        voice="alloy",  # Not used in text-only mode, but kept for fallback
        text_only=True   # Always use text-only output for avatar integration
    )

    if not conversation_started:
        logger.error(f"Failed to start conversation for session {session_id}")
        await websocket.send_json({"error": "Failed to start conversation"})
        await websocket.close()
        return

    logger.info(f"OpenAI conversation ready for session: {session_id} (text-only mode)")

    # Get database session for saving messages
    db_gen = get_db()
    db = await db_gen.__anext__()

    # Convert session_id string to UUID
    thread_uuid = uuid.UUID(session_id)

    # Callback to send OpenAI LLM text responses to frontend AND save to database
    async def forward_text_response_to_client(text_response: str):
        """
        Forward OpenAI LLM text response to frontend and save to database.
        Frontend will use this with avatar.speak(text)
        """
        try:
            logger.info(f"📝 Sending text response to client: '{text_response[:100]}...'")

            # Save assistant message to database
            try:
                await MessageService.create_message(
                    db=db,
                    thread_id=thread_uuid,
                    role="assistant",
                    content=text_response
                )
                logger.info(f"💾 Saved assistant message to database for session {session_id}")
            except Exception as db_error:
                logger.error(f"Failed to save assistant message to database: {db_error}")

            # Send to frontend
            await websocket.send_json({
                "type": "text_response",
                "text": text_response
            })
        except Exception as e:
            logger.error(f"Error forwarding text response to client {session_id}: {e}")

    # Forward user input transcripts to frontend AND save to database
    async def forward_transcript_to_client(transcript: str):
        """Forward user input transcript to frontend and save to database."""
        try:
            logger.info(f"🎤 User said: '{transcript}'")

            # Save user message to database
            try:
                await MessageService.create_message(
                    db=db,
                    thread_id=thread_uuid,
                    role="user",
                    content=transcript
                )
                logger.info(f"💾 Saved user message to database for session {session_id}")
            except Exception as db_error:
                logger.error(f"Failed to save user message to database: {db_error}")

            # Send to frontend
            await websocket.send_json({
                "type": "transcript",
                "text": transcript
            })
        except Exception as e:
            logger.error(f"Error forwarding transcript to client {session_id}: {e}")

    # Set up callbacks
    openai_service.set_text_response_callback(forward_text_response_to_client)
    openai_service.set_transcript_callback(forward_transcript_to_client)

    # Start listening for OpenAI events
    openai_service.start_listening()

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
                    # Commit the audio buffer to trigger OpenAI response
                    await openai_service.commit_audio_buffer()
                    await websocket.send_json({"type": "recording_stopped"})

            # Handle binary messages (audio data)
            elif "bytes" in message:
                audio_data = message["bytes"]
                logger.debug(f"Received {len(audio_data)} bytes of audio from session {session_id}")

                # Forward audio to OpenAI for ASR + LLM processing
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
        await db.close()

    except Exception as e:
        logger.error(f"Error in WebSocket connection for session {session_id}: {e}")
        await openai_service.disconnect()
        await db.close()
        # Only close if not already disconnected
        try:
            await websocket.close()
        except RuntimeError:
            pass  # WebSocket already closed
