"""
HeyGen API endpoints
Provides session token generation for HeyGen Streaming Avatar SDK
"""
from fastapi import APIRouter, HTTPException
import httpx
from app.core.config import settings

router = APIRouter()


@router.post("/session-token")
async def create_heygen_session_token():
    """
    Create a HeyGen streaming session token for frontend use.

    This endpoint calls HeyGen's API to generate a session token that the frontend
    can use with the @heygen/streaming-avatar SDK.

    Returns:
        dict: Contains the session token

    Raises:
        HTTPException: If token generation fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.heygen.com/v1/streaming.create_token",
                headers={
                    "X-Api-Key": settings.HEYGEN_API_KEY,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"HeyGen API error: {response.text}"
                )

            data = response.json()
            token = data.get("data", {}).get("token")

            if not token:
                raise HTTPException(
                    status_code=500,
                    detail="No token returned from HeyGen API"
                )

            return {"token": token}

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to HeyGen API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/sessions")
async def list_heygen_sessions():
    """
    List all active HeyGen streaming sessions.

    Returns:
        dict: List of active sessions

    Raises:
        HTTPException: If API call fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.heygen.com/v1/streaming.list",
                headers={
                    "X-Api-Key": settings.HEYGEN_API_KEY,
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"HeyGen API error: {response.text}"
                )

            return response.json()

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to HeyGen API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def stop_heygen_session(session_id: str):
    """
    Stop a specific HeyGen streaming session.

    Args:
        session_id: The session ID to stop

    Returns:
        dict: Success message

    Raises:
        HTTPException: If API call fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.heygen.com/v1/streaming.stop",
                headers={
                    "X-Api-Key": settings.HEYGEN_API_KEY,
                    "Content-Type": "application/json"
                },
                json={"session_id": session_id},
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"HeyGen API error: {response.text}"
                )

            return {"message": f"Session {session_id} stopped successfully"}

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to HeyGen API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/cleanup-sessions")
async def cleanup_all_heygen_sessions():
    """
    Stop all active HeyGen streaming sessions.

    Returns:
        dict: Number of sessions closed

    Raises:
        HTTPException: If API call fails
    """
    try:
        async with httpx.AsyncClient() as client:
            # First, list all sessions
            list_response = await client.get(
                "https://api.heygen.com/v1/streaming.list",
                headers={
                    "X-Api-Key": settings.HEYGEN_API_KEY,
                },
                timeout=30.0
            )

            if list_response.status_code != 200:
                raise HTTPException(
                    status_code=list_response.status_code,
                    detail=f"HeyGen API error: {list_response.text}"
                )

            sessions_data = list_response.json()
            sessions = sessions_data.get("data", {}).get("sessions", [])

            # Stop each session
            closed_count = 0
            errors = []

            for session in sessions:
                session_id = session.get("session_id")
                if session_id:
                    try:
                        stop_response = await client.delete(
                            f"https://api.heygen.com/v1/streaming.stop",
                            headers={
                                "X-Api-Key": settings.HEYGEN_API_KEY,
                                "Content-Type": "application/json"
                            },
                            json={"session_id": session_id},
                            timeout=30.0
                        )

                        if stop_response.status_code == 200:
                            closed_count += 1
                        else:
                            errors.append(f"Failed to stop {session_id}: {stop_response.text}")
                    except Exception as e:
                        errors.append(f"Error stopping {session_id}: {str(e)}")

            return {
                "message": f"Cleanup completed",
                "sessions_found": len(sessions),
                "sessions_closed": closed_count,
                "errors": errors if errors else None
            }

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to HeyGen API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
