import asyncio
import json
import base64
from typing import Optional, Callable, Any
import websockets
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HeyGenStreamingService:
    """
    Service for managing HeyGen Streaming Avatar sessions for converting audio to video.
    """

    def __init__(self):
        """Initialize the HeyGen Streaming service."""
        self.api_key = settings.HEYGEN_API_KEY
        self.session_id: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.realtime_endpoint: Optional[str] = None
        self.is_connected = False
        self.video_callback: Optional[Callable[[bytes], Any]] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._event_id_counter = 0

    async def create_session(
        self,
        avatar_id: Optional[str] = None,
        quality: str = "medium",
        voice_id: Optional[str] = None
    ) -> bool:
        """
        Create a new HeyGen streaming session.

        Args:
            avatar_id: Optional avatar ID (uses default if not provided)
            quality: Video quality - "low", "medium", or "high"
            voice_id: Optional voice ID

        Returns:
            bool: True if session created successfully
        """
        try:
            logger.info("Creating HeyGen streaming session...")

            # Prepare request body
            request_body = {
                "quality": quality,
                "video_encoding": "H264"
            }

            if avatar_id:
                request_body["avatar_id"] = avatar_id
            if voice_id:
                request_body["voice_id"] = voice_id

            # Create session via HeyGen API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.heygen.com/v1/streaming.new",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=request_body,
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(f"Failed to create HeyGen session: {response.status_code} - {response.text}")
                    return False

                session_data = response.json()
                logger.info(f"HeyGen session response: {session_data}")

                # Extract session details
                data = session_data.get("data", {})
                self.session_id = data.get("session_id")
                self.realtime_endpoint = data.get("realtime_endpoint")

                if not self.session_id or not self.realtime_endpoint:
                    logger.error("Missing session_id or realtime_endpoint in response")
                    return False

                logger.info(f"✓ HeyGen session created: {self.session_id}")
                return True

        except Exception as e:
            logger.error(f"Error creating HeyGen session: {e}")
            return False

    async def connect(self) -> bool:
        """
        Connect to HeyGen WebSocket for audio-to-video streaming.

        Returns:
            bool: True if connected successfully
        """
        try:
            if not self.realtime_endpoint:
                logger.error("No realtime_endpoint available. Create a session first.")
                return False

            logger.info(f"Connecting to HeyGen WebSocket: {self.realtime_endpoint}")

            # Connect to HeyGen WebSocket
            self.websocket = await websockets.connect(self.realtime_endpoint)
            self.is_connected = True

            logger.info("✓ Connected to HeyGen WebSocket")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to HeyGen WebSocket: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from HeyGen WebSocket."""
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
            self.video_callback = None
            self.session_id = None
            self.realtime_endpoint = None

            logger.info("Disconnected from HeyGen WebSocket")

        except Exception as e:
            logger.error(f"Error disconnecting from HeyGen: {e}")

    async def send_audio_chunk(self, audio_data: bytes) -> bool:
        """
        Send audio chunk to HeyGen for video generation.

        Args:
            audio_data: Raw PCM16 audio bytes (mono, 24kHz)

        Returns:
            bool: True if sent successfully
        """
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("Not connected to HeyGen WebSocket")
                return False

            # Encode audio to base64 as required by HeyGen
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Generate unique event ID
            self._event_id_counter += 1
            event_id = f"audio_{self._event_id_counter}"

            # Send agent.speak event to HeyGen
            event = {
                "type": "agent.speak",
                "event_id": event_id,
                "audio": audio_base64
            }

            await self.websocket.send(json.dumps(event))
            logger.debug(f"Sent {len(audio_data)} bytes of audio to HeyGen (event_id: {event_id})")

            return True

        except Exception as e:
            logger.error(f"Error sending audio to HeyGen: {e}")
            return False

    async def finish_audio_stream(self) -> bool:
        """
        Signal that audio stream is complete.

        Returns:
            bool: True if signaled successfully
        """
        try:
            if not self.is_connected or not self.websocket:
                logger.warning("Not connected to HeyGen WebSocket")
                return False

            # Send agent.speak_end event
            event = {
                "type": "agent.speak_end"
            }

            await self.websocket.send(json.dumps(event))
            logger.info("Signaled end of audio stream to HeyGen")

            return True

        except Exception as e:
            logger.error(f"Error finishing audio stream: {e}")
            return False

    def set_video_callback(self, callback: Callable[[bytes], Any]) -> None:
        """
        Set callback function to be called when video is received from HeyGen.

        Args:
            callback: Async function to call with received video data
        """
        self.video_callback = callback
        logger.debug("Video callback registered")

    async def _listen_for_events(self) -> None:
        """
        Internal method to continuously listen for events from HeyGen.
        This runs in a background task.
        """
        try:
            logger.info("Started listening for events from HeyGen")

            while self.is_connected and self.websocket:
                try:
                    # Receive message from HeyGen WebSocket
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=1.0
                    )

                    # HeyGen sends both text events and binary video data
                    if isinstance(message, bytes):
                        # Binary video data
                        logger.debug(f"Received {len(message)} bytes of video data from HeyGen")
                        if self.video_callback:
                            await self.video_callback(message)
                    else:
                        # Text event
                        event = json.loads(message)
                        event_type = event.get("type")
                        logger.debug(f"Received event from HeyGen: {event_type}")

                        if event_type == "session.state_updated":
                            state = event.get("state")
                            logger.info(f"HeyGen session state: {state}")

                        elif event_type == "agent.audio_buffer_appended":
                            logger.debug("Audio chunk buffered by HeyGen")

                        elif event_type == "agent.audio_buffer_committed":
                            logger.info("Audio buffer committed by HeyGen")

                        elif event_type == "agent.speak_started":
                            logger.info("HeyGen avatar started speaking")

                        elif event_type == "agent.speak_ended":
                            logger.info("HeyGen avatar finished speaking")

                        elif event_type == "error":
                            error_info = event.get("error", {})
                            logger.error(f"HeyGen error: {error_info}")

                        elif event_type == "warning":
                            logger.warning(f"HeyGen warning: {event}")

                except asyncio.TimeoutError:
                    # Timeout is expected, just continue the loop
                    continue

        except asyncio.CancelledError:
            logger.debug("HeyGen listening task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in HeyGen listening loop: {e}")

    def start_listening(self) -> None:
        """Start background task to listen for events from HeyGen."""
        if not self._listen_task or self._listen_task.done():
            self._listen_task = asyncio.create_task(self._listen_for_events())
            logger.info("Started HeyGen listening task")


# Singleton instance
_heygen_service: Optional[HeyGenStreamingService] = None


def get_heygen_service() -> HeyGenStreamingService:
    """
    Get or create the HeyGen Streaming service singleton.

    Returns:
        HeyGenStreamingService: The service instance
    """
    global _heygen_service
    if _heygen_service is None:
        _heygen_service = HeyGenStreamingService()
    return _heygen_service
