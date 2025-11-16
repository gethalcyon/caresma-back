import asyncio
from typing import Optional, Callable, Any
import httpx
from livekit import rtc
from PIL import Image
import io
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HeyGenLiveKitService:
    """
    Service for managing HeyGen avatar sessions using LiveKit for video streaming.
    This connects to HeyGen's LiveKit infrastructure and streams video to the frontend.
    """

    def __init__(self):
        """Initialize the HeyGen LiveKit service."""
        self.api_key = settings.HEYGEN_API_KEY
        self.session_id: Optional[str] = None
        self.room: Optional[rtc.Room] = None
        self.livekit_url: Optional[str] = None
        self.access_token: Optional[str] = None
        self.is_connected = False
        self.video_callback: Optional[Callable[[bytes], Any]] = None
        self._video_track: Optional[rtc.RemoteVideoTrack] = None
        self._avatar_ready = False  # Track when avatar is ready to receive text

    async def create_session(
        self,
        avatar_id: Optional[str] = None,
        quality: str = "medium",
        voice_id: Optional[str] = None
    ) -> bool:
        """
        Create a new HeyGen streaming session and get LiveKit credentials.

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
                logger.info(f"HeyGen session created successfully")

                # Extract session details
                data = session_data.get("data", {})
                self.session_id = data.get("session_id")
                self.livekit_url = data.get("url")  # LiveKit server URL
                self.access_token = data.get("access_token")  # LiveKit access token

                if not self.session_id or not self.livekit_url or not self.access_token:
                    logger.error("Missing required session data from HeyGen response")
                    return False

                logger.info(f"✓ HeyGen session created: {self.session_id}")
                logger.info(f"✓ LiveKit URL: {self.livekit_url}")
                return True

        except Exception as e:
            logger.error(f"Error creating HeyGen session: {e}")
            return False

    async def connect(self) -> bool:
        """
        Connect to LiveKit room to receive video stream from HeyGen.

        Returns:
            bool: True if connected successfully
        """
        try:
            if not self.livekit_url or not self.access_token:
                logger.error("No LiveKit credentials available. Create a session first.")
                return False

            logger.info(f"Connecting to LiveKit room...")

            # Create LiveKit room
            self.room = rtc.Room()

            # Set up event handlers
            @self.room.on("track_subscribed")
            def on_track_subscribed(
                track: rtc.Track,
                publication: rtc.RemoteTrackPublication,
                participant: rtc.RemoteParticipant
            ):
                logger.info(f"Track subscribed: {track.kind} from {participant.identity}")

                if track.kind == rtc.TrackKind.KIND_VIDEO:
                    self._video_track = track
                    logger.info("✓ Video track subscribed")
                    # Start processing video frames
                    asyncio.create_task(self._process_video_frames(track))

                    # Mark avatar as ready to receive text
                    if not self._avatar_ready:
                        self._avatar_ready = True
                        logger.info("🎬 Avatar is now ready to receive text tasks")

            @self.room.on("track_unsubscribed")
            def on_track_unsubscribed(
                track: rtc.Track,
                publication: rtc.RemoteTrackPublication,
                participant: rtc.RemoteParticipant
            ):
                logger.info(f"Track unsubscribed: {track.kind}")

            @self.room.on("participant_connected")
            def on_participant_connected(participant: rtc.RemoteParticipant):
                logger.info(f"Participant connected: {participant.identity}")

            @self.room.on("disconnected")
            def on_disconnected():
                logger.info("Disconnected from LiveKit room")
                self.is_connected = False

            # Connect to the room
            await self.room.connect(self.livekit_url, self.access_token)
            self.is_connected = True

            logger.info("✓ Connected to LiveKit room")
            logger.info("⏳ Waiting for avatar to publish video track...")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to LiveKit: {e}")
            self.is_connected = False
            return False

    async def _process_video_frames(self, track: rtc.RemoteVideoTrack):
        """
        Process video frames from LiveKit and forward to frontend.

        Args:
            track: Remote video track from LiveKit
        """
        try:
            logger.info("Started processing video frames")

            async for frame in track:
                if not self.is_connected:
                    break

                try:
                    # Convert video frame to numpy array (RGB format)
                    buffer = frame.to_ndarray(format="rgb24")
                    logger.debug(f"Received video frame: {buffer.shape}")

                    # Convert numpy array to PIL Image
                    image = Image.fromarray(buffer, mode='RGB')

                    # Encode as JPEG with quality 90 (good balance between size and quality)
                    jpeg_buffer = io.BytesIO()
                    image.save(jpeg_buffer, format='JPEG', quality=90, optimize=True)
                    jpeg_data = jpeg_buffer.getvalue()

                    logger.debug(f"Encoded JPEG frame: {len(jpeg_data)} bytes")

                    # Send via callback to WebSocket endpoint
                    if self.video_callback:
                        await self.video_callback(jpeg_data)

                except Exception as e:
                    logger.error(f"Error processing video frame: {e}")

        except Exception as e:
            logger.error(f"Error in video frame processing loop: {e}")

    async def disconnect(self):
        """Disconnect from LiveKit room and stop HeyGen session."""
        try:
            if self.room:
                await self.room.disconnect()
                self.room = None

            # Stop the HeyGen session via API
            if self.session_id:
                await self.stop_session()

            self.is_connected = False
            self.video_callback = None
            self._video_track = None
            self._avatar_ready = False

            logger.info("Disconnected from HeyGen LiveKit session")

        except Exception as e:
            logger.error(f"Error disconnecting from HeyGen: {e}")

    async def stop_session(self) -> bool:
        """
        Stop the current HeyGen session to free up resources.

        Returns:
            bool: True if session stopped successfully
        """
        try:
            if not self.session_id:
                logger.warning("No session to stop")
                return False

            logger.info(f"Stopping HeyGen session: {self.session_id}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.heygen.com/v1/streaming.stop",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "session_id": self.session_id
                    },
                    timeout=10.0
                )

                if response.status_code != 200:
                    logger.warning(f"Failed to stop HeyGen session: {response.status_code} - {response.text}")
                    return False

                logger.info(f"✓ HeyGen session stopped: {self.session_id}")
                self.session_id = None
                return True

        except Exception as e:
            logger.error(f"Error stopping HeyGen session: {e}")
            return False

    async def send_text(self, text: str, task_type: str = "repeat") -> bool:
        """
        Send text to HeyGen for avatar to speak.
        HeyGen will handle text-to-speech conversion and generate the avatar video.

        Args:
            text: Text for the avatar to speak
            task_type: Task type - "repeat" (speaks exactly as given) or "talk" (processes through LLM)

        Returns:
            bool: True if sent successfully
        """
        try:
            if not self.is_connected or not self.session_id:
                logger.warning("Not connected to HeyGen session")
                return False

            if not text or not text.strip():
                logger.warning("Empty text provided, skipping HeyGen request")
                return False

            # Check if avatar is ready
            if not self._avatar_ready:
                logger.warning(f"⏳ Avatar not ready yet, cannot send text ({len(text)} chars)")
                return False

            # Send text to HeyGen API
            payload = {
                "session_id": self.session_id,
                "text": text,
                "task_type": task_type
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.heygen.com/v1/streaming.task",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10.0
                )

                if response.status_code != 200:
                    logger.error(f"Failed to send text to HeyGen: {response.status_code} - {response.text}")
                    return False

                logger.info(f"✅ Sent text to HeyGen: '{text[:50]}...' ({len(text)} chars)")
                return True

        except Exception as e:
            logger.error(f"Error sending text to HeyGen: {e}")
            return False

    def start_listening(self) -> None:
        """
        Start listening for video frames from LiveKit.
        Note: Video processing starts automatically when track is subscribed.
        This method is provided for API compatibility.
        """
        logger.debug("HeyGen LiveKit service is listening (video processing started automatically)")

    def set_video_callback(self, callback: Callable[[bytes], Any]) -> None:
        """
        Set callback function to be called when video data is received.

        Args:
            callback: Async function to call with received video data
        """
        self.video_callback = callback
        logger.debug("Video callback registered")

    def set_audio_callback(self, callback: Callable[[bytes], Any]) -> None:
        """
        Set callback function to be called when audio data is received.

        Args:
            callback: Async function to call with received audio data
        """
        self.audio_callback = callback
        logger.debug("Audio callback registered")

    def get_connection_status(self) -> dict:
        """
        Get the current connection status.

        Returns:
            dict: Connection status information
        """
        return {
            "connected": self.is_connected,
            "session_id": self.session_id,
            "has_video_track": self._video_track is not None,
            "has_audio_track": self._audio_track is not None,
        }


# Singleton instance
_heygen_livekit_service: Optional[HeyGenLiveKitService] = None


def get_heygen_livekit_service() -> HeyGenLiveKitService:
    """
    Get or create the HeyGen LiveKit service singleton.

    Returns:
        HeyGenLiveKitService: The service instance
    """
    global _heygen_livekit_service
    if _heygen_livekit_service is None:
        _heygen_livekit_service = HeyGenLiveKitService()
    return _heygen_livekit_service
