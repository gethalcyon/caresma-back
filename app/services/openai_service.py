import asyncio
import json
import base64
from typing import Optional, Callable, Any
import websockets
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIRealtimeService:
    """
    Service for managing OpenAI Realtime API connections for audio streaming.
    """

    def __init__(self):
        """Initialize the OpenAI Realtime service."""
        self.client = None  # Will be initialized when needed
        self.websocket = None
        self.is_connected = False
        self.api_key = settings.OPENAI_API_KEY
        self.audio_callback: Optional[Callable[[bytes], Any]] = None
        self.text_response_callback: Optional[Callable[[str], Any]] = None  # For LLM text responses
        self.transcript_callback: Optional[Callable[[str], Any]] = None  # For user input transcripts
        self._listen_task: Optional[asyncio.Task] = None
        self.session_config: Optional[dict] = None
        self._current_transcript = ""  # Accumulate user input transcript deltas
        self._current_response_text = ""  # Accumulate LLM response text deltas

    async def connect(self) -> bool:
        """
        Establish connection to OpenAI Realtime API.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Connecting to OpenAI Realtime API...")

            # OpenAI Realtime API endpoint
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

            # Connect to OpenAI WebSocket with API key in headers
            additional_headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            self.websocket = await websockets.connect(
                url,
                additional_headers=additional_headers
            )
            self.is_connected = True
            logger.info("✓ Connected to OpenAI Realtime API")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to OpenAI Realtime API: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from OpenAI Realtime API."""
        try:
            # Cancel the listening task if it's running
            if self._listen_task and not self._listen_task.done():
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass

            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            self.is_connected = False
            self.audio_callback = None
            self.text_response_callback = None
            self.transcript_callback = None
            self._current_transcript = ""
            self._current_response_text = ""
            logger.info("Disconnected from OpenAI Realtime API")

        except Exception as e:
            logger.error(f"Error disconnecting from OpenAI: {e}")

    async def send_audio(self, audio_data: bytes) -> bool:
        """
        Send audio data to OpenAI for processing.

        Args:
            audio_data: Raw PCM16 audio bytes from browser (mono, 24kHz)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("Not connected to OpenAI Realtime API")
                return False

            # Browser now sends PCM16 audio directly
            # Encode audio data to base64 as required by OpenAI
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Send input_audio_buffer.append event to OpenAI
            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }

            await self.websocket.send(json.dumps(event))
            logger.debug(f"Sent {len(audio_data)} bytes of PCM16 audio to OpenAI")

            return True

        except Exception as e:
            logger.error(f"Error sending audio to OpenAI: {e}")
            return False

    async def commit_audio_buffer(self) -> bool:
        """
        Commit the audio buffer to trigger OpenAI to process and respond.

        Returns:
            bool: True if committed successfully
        """
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("Not connected to OpenAI Realtime API")
                return False

            # Send input_audio_buffer.commit event
            event = {
                "type": "input_audio_buffer.commit"
            }

            await self.websocket.send(json.dumps(event))
            logger.info("Committed audio buffer to OpenAI")

            return True

        except Exception as e:
            logger.error(f"Error committing audio buffer: {e}")
            return False

    def set_audio_callback(self, callback: Callable[[bytes], Any]) -> None:
        """
        Set callback function to be called when audio is received from OpenAI.

        Args:
            callback: Async function to call with received audio data
        """
        self.audio_callback = callback
        logger.debug("Audio callback registered")

    def set_transcript_callback(self, callback: Callable[[str], Any]) -> None:
        """
        Set callback function to be called when a complete user input transcript is received from OpenAI.

        Args:
            callback: Async function to call with received transcript text
        """
        self.transcript_callback = callback
        logger.debug("Transcript callback registered")

    def set_text_response_callback(self, callback: Callable[[str], Any]) -> None:
        """
        Set callback function to be called when a complete LLM text response is received from OpenAI.

        Args:
            callback: Async function to call with received LLM response text
        """
        self.text_response_callback = callback
        logger.debug("Text response callback registered")

    async def _listen_for_audio(self) -> None:
        """
        Internal method to continuously listen for response from openai
        This runs in a background task.
        """
        try:
            logger.info("Started listening for audio from OpenAI")

            while self.is_connected and self.websocket:
                try:
                    # Receive message from OpenAI WebSocket
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0  # Timeout to allow checking is_connected periodically
                    )

                    # Parse the message
                    event = json.loads(message)
                    event_type = event.get("type")

                    logger.debug(f"Received event from OpenAI: {event_type}")

                    # Handle different event types
                    if event_type == "response.audio.delta":
                        # Audio chunk from OpenAI (only used if audio output is enabled)
                        audio_base64 = event.get("delta")
                        if audio_base64 and self.audio_callback:
                            # Decode base64 audio
                            audio_data = base64.b64decode(audio_base64)
                            await self.audio_callback(audio_data)

                    elif event_type == "response.text.delta":
                        # Text response delta from OpenAI LLM - accumulate it
                        delta_text = event.get("delta", "")
                        if delta_text:
                            self._current_response_text += delta_text
                            logger.debug(f"Accumulated LLM response: {self._current_response_text}")
                
                    elif event_type == "response.text.done":
                        # LLM text response complete - send to callback
                        logger.info(f"OpenAI text response done: {self._current_response_text}")
                        if self._current_response_text and self.text_response_callback:
                            await self.text_response_callback(self._current_response_text)
                        # Reset for next response
                        self._current_response_text = ""

                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # User input transcript complete
                        transcript_text = event.get("transcript", "")
                        if transcript_text:
                            logger.info(f"User input transcript: {transcript_text}")
                            if self.transcript_callback:
                                await self.transcript_callback(transcript_text)

                    elif event_type == "response.audio.done":
                        logger.info("OpenAI finished sending audio response")

                    elif event_type == "response.done":
                        logger.info("OpenAI response complete")

                    elif event_type == "error":
                        error_info = event.get("error", {})
                        logger.error(f"OpenAI error: {error_info}")

                    elif event_type == "session.created":
                        logger.info("OpenAI session created")

                    elif event_type == "session.updated":
                        logger.info("OpenAI session updated")

                    elif event_type == "conversation.item.created":
                        logger.debug("Conversation item created")

                    elif event_type == "response.created":
                        logger.info("OpenAI response created")

                except asyncio.TimeoutError:
                    # Timeout is expected, just continue the loop
                    continue

        except asyncio.CancelledError:
            logger.debug("Audio listening task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in audio listening loop: {e}")

    def start_listening(self) -> None:
        """Start background task to listen for audio from OpenAI."""
        if not self._listen_task or self._listen_task.done():
            self._listen_task = asyncio.create_task(self._listen_for_audio())
            logger.info("Started audio listening task")

    async def start_conversation(
        self,
        system_prompt: Optional[str] = None,
        voice: str = "alloy",
        text_only: bool = True
    ) -> bool:
        """
        Initialize a new conversation with OpenAI.

        Args:
            system_prompt: Optional system prompt for the conversation
            voice: Voice to use for TTS (alloy, echo, fable, onyx, nova, shimmer)
            text_only: If True, use text-only output (for HeyGen TTS). If False, use audio output.

        Returns:
            bool: True if conversation started successfully
        """
        try:
            if not self.is_connected:
                await self.connect()

            if not self.websocket:
                logger.error("WebSocket not available")
                return False

            # Configuration for the session
            if text_only:
                # Text-only mode: OpenAI does ASR, returns text response
                # HeyGen will handle TTS + lipsync + video generation
                self.session_config = {
                    "modalities": ["text"],  # Text-only output (no audio from OpenAI)
                    "instructions": system_prompt or "You are a helpful assistant that responds in text only.",
                    "input_audio_format": "pcm16",  # Still accept audio input for ASR
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            else:
                # Audio mode: OpenAI does ASR + LLM + TTS
                self.session_config = {
                    "modalities": ["text", "audio"],
                    "instructions": system_prompt or "You are a helpful assistant.",
                    "voice": voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }

            # Send session.update event to configure the session
            event = {
                "type": "session.update",
                "session": self.session_config
            }

            await self.websocket.send(json.dumps(event))

            if text_only:
                logger.info("Started conversation in text-only mode (audio input → text output)")
            else:
                logger.info(f"Started conversation in audio mode with voice: {voice}")

            return True

        except Exception as e:
            logger.error(f"Error starting conversation: {e}")
            return False

    def get_connection_status(self) -> dict:
        """
        Get the current connection status.

        Returns:
            dict: Connection status information
        """
        return {
            "connected": self.is_connected,
            "api_key_configured": bool(settings.OPENAI_API_KEY),
        }


# Singleton instance
_openai_service: Optional[OpenAIRealtimeService] = None


def get_openai_service() -> OpenAIRealtimeService:
    """
    Get or create the OpenAI Realtime service singleton.

    Returns:
        OpenAIRealtimeService: The service instance
    """
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIRealtimeService()
    return _openai_service
