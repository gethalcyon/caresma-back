#!/usr/bin/env python3
"""
Utility script to list and stop all active HeyGen sessions.
This is useful when you hit the concurrent session limit.
"""
import asyncio
import httpx
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings


async def list_sessions():
    """List all active HeyGen sessions."""
    try:
        print("Fetching active HeyGen sessions...")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.heygen.com/v1/streaming.list",
                headers={
                    "X-Api-Key": settings.HEYGEN_API_KEY,
                },
                timeout=30.0
            )

            if response.status_code != 200:
                print(f"❌ Failed to list sessions: {response.status_code}")
                print(f"Response: {response.text}")
                return []

            data = response.json()
            sessions = data.get("data", {}).get("sessions", [])

            if not sessions:
                print("✓ No active sessions found")
                return []

            print(f"\n📋 Found {len(sessions)} active session(s):")
            for i, session in enumerate(sessions, 1):
                session_id = session.get("session_id", "Unknown")
                status = session.get("status", "Unknown")
                created_at = session.get("created_at", "Unknown")
                print(f"  {i}. Session ID: {session_id}")
                print(f"     Status: {status}")
                print(f"     Created: {created_at}")
                print()

            return sessions

    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        return []


async def stop_session(session_id: str):
    """Stop a specific HeyGen session."""
    try:
        print(f"Stopping session: {session_id}...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.heygen.com/v1/streaming.stop",
                headers={
                    "X-Api-Key": settings.HEYGEN_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "session_id": session_id
                },
                timeout=10.0
            )

            if response.status_code != 200:
                print(f"❌ Failed to stop session {session_id}: {response.status_code}")
                print(f"Response: {response.text}")
                return False

            print(f"✓ Session {session_id} stopped successfully")
            return True

    except Exception as e:
        print(f"❌ Error stopping session {session_id}: {e}")
        return False


async def stop_all_sessions():
    """Stop all active HeyGen sessions."""
    sessions = await list_sessions()

    if not sessions:
        return

    print("\n🧹 Stopping all sessions...")

    for session in sessions:
        session_id = session.get("session_id")
        if session_id:
            await stop_session(session_id)
            await asyncio.sleep(0.5)  # Small delay between requests

    print("\n✅ All sessions have been processed")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("HeyGen Session Cleanup Utility")
    print("=" * 60)
    print()

    # List current sessions
    sessions = await list_sessions()

    if not sessions:
        print("\n✓ No cleanup needed - no active sessions")
        return

    # Ask user if they want to stop all sessions
    print("\n⚠️  Do you want to stop all active sessions? (yes/no): ", end="")
    choice = input().strip().lower()

    if choice in ["yes", "y"]:
        await stop_all_sessions()
    else:
        print("\n❌ Cleanup cancelled")


if __name__ == "__main__":
    asyncio.run(main())
