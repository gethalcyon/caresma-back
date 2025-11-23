# Caresma Avatar Chat - Implementation Plan

This document outlines the step-by-step implementation plan to build the real-time avatar chatting system described in [ARCHITECTURE.md](./ARCHITECTURE.md).

## Overview

The goal is to build a system where users can have voice conversations with an AI-powered avatar. The system integrates:
- OpenAI Realtime API for speech-to-text and LLM responses
- HeyGen Streaming Avatar for video rendering and text-to-speech
- FastAPI backend for WebSocket management
- React frontend for user interface

---

## Phase 1: Backend Foundation

### 1.1 Project Setup
- [ ] Initialize FastAPI project structure
- [ ] Set up configuration management (`app/core/config.py`)
- [ ] Configure logging (`app/core/logging.py`)
- [ ] Set up environment variables (`.env`)
  - `OPENAI_API_KEY`
  - `HEYGEN_API_KEY`
  - `DATABASE_URL`

### 1.2 Database Setup
- [ ] Configure PostgreSQL connection (`app/db/session.py`)
- [ ] Create database models:
  - `messages` table with fields: `id`, `thread_id`, `role`, `content`, `created_at`
- [ ] Set up Alembic for migrations
- [ ] Create MessageService for CRUD operations (`app/services/Messages.py`)

### 1.3 OpenAI Realtime Service
- [ ] Create `OpenAIRealtimeService` class (`app/services/openai_service.py`)
- [ ] Implement WebSocket connection to OpenAI Realtime API
- [ ] Implement session configuration with VAD settings:
  ```python
  "turn_detection": {
      "type": "server_vad",
      "threshold": 0.5,
      "prefix_padding_ms": 300,
      "silence_duration_ms": 500
  }
  ```
- [ ] Implement audio streaming (`send_audio`, `commit_audio_buffer`)
- [ ] Implement background listener task (`_listen_for_audio`)
- [ ] Handle OpenAI events:
  - `response.text.delta` - accumulate text
  - `response.text.done` - send complete response
  - `conversation.item.input_audio_transcription.completed` - user transcript
- [ ] Implement callback system for responses
- [ ] **Multi-session support**: Use session-based dictionary instead of singleton
  ```python
  _openai_services: dict[str, OpenAIRealtimeService] = {}
  ```
- [ ] Implement `cleanup_openai_service(session_id)` for cleanup

---

## Phase 2: WebSocket Endpoint

### 2.1 WebSocket Handler
- [ ] Create WebSocket endpoint (`app/api/v1/websocket.py`)
- [ ] Route: `/ws/session/{session_id}`
- [ ] Implement connection lifecycle:
  1. Accept WebSocket connection
  2. Generate/validate session UUID
  3. Connect to OpenAI Realtime API
  4. Set up response callbacks
  5. Start background listener
  6. Enter main loop for audio streaming

### 2.2 Session Management
- [ ] Handle session ID validation:
  - Accept existing UUID
  - Generate new UUID for "new", "undefined", "null", ""
- [ ] Send `session_created` event to frontend with generated UUID
- [ ] Link all messages to session via `thread_uuid`

### 2.3 Message Handling
- [ ] Handle text messages (control messages):
  - `ping` -> `pong`
  - `start_recording` -> `recording_started`
  - `stop_recording` -> commit audio buffer, `recording_stopped`
- [ ] Handle binary messages (audio data):
  - Forward PCM16 audio to OpenAI service
- [ ] Forward responses to frontend:
  - `text_response` - AI response text
  - `transcript` - user speech transcript

### 2.4 Database Integration
- [ ] Save user messages (role: "user") on transcript received
- [ ] Save assistant messages (role: "assistant") on text response received
- [ ] Proper cleanup on disconnect

---

## Phase 3: Frontend Foundation

### 3.1 Project Setup
- [ ] Initialize React project (Create React App or Vite)
- [ ] Set up project structure:
  ```
  src/
  ├── components/
  ├── hooks/
  ├── services/
  └── App.js
  ```
- [ ] Configure environment variables
  - `REACT_APP_API_URL`

### 3.2 WebSocket Hook
- [ ] Create `useOpenAIWebSocket.js` hook
- [ ] Implement WebSocket connection management
- [ ] Implement audio capture using Web Audio API:
  - Request microphone access
  - Create AudioContext at 24kHz (OpenAI requirement)
  - Convert Float32 to PCM16 Int16Array
- [ ] Stream audio to backend via WebSocket
- [ ] Handle incoming events:
  - `text_response` - AI response
  - `transcript` - user speech
  - `session_created` - session UUID from backend
  - `recording_started` / `recording_stopped`
  - `error`
- [ ] Implement callback system (`setOnTextResponse`, `setOnTranscript`, `setOnSessionCreated`)
- [ ] Implement cleanup on unmount

---

## Phase 4: HeyGen Avatar Integration

### 4.1 HeyGen Setup
- [ ] Install `@heygen/streaming-avatar` SDK
- [ ] Create HeyGen API endpoints in backend for token management

### 4.2 Avatar Hook
- [ ] Create `useHeygenAvatar.js` hook
- [ ] Initialize StreamingAvatar SDK
- [ ] Implement avatar session creation
- [ ] Implement `speak(text)` function for text-to-speech
- [ ] Handle avatar video stream (WebRTC)
- [ ] Track avatar states: `ready`, `loading`, `error`, `isSpeaking`
- [ ] Implement `closeAvatar()` for cleanup

---

## Phase 5: Main UI Component

### 5.1 Home Component
- [ ] Create `Home.js` main component
- [ ] Implement session state management:
  - `sessionStarted`
  - `sessionId`
  - `userTranscript`
  - `aiResponse`
  - `greetingDone`

### 5.2 Hook Integration
- [ ] Initialize `useOpenAIWebSocket` when session starts
- [ ] Initialize `useHeygenAvatar` when session starts
- [ ] Wire up callbacks:
  - On `text_response` -> call `speak(text)` + display in UI
  - On `transcript` -> display in UI
  - On `session_created` -> update `sessionId` state

### 5.3 UI Elements
- [ ] Avatar video container with video element
- [ ] Conversation display (user + assistant messages)
- [ ] Control buttons:
  - "Start Session" - initialize everything
  - "Start Speaking" - begin recording (disabled until greeting done)
  - "End Session" - cleanup and reset
- [ ] Status indicator (connected, speaking, listening, etc.)
- [ ] Loading and error states

### 5.4 Greeting Flow
- [ ] When avatar ready + WebSocket connected:
  - Avatar speaks greeting: "Hello [Name], how do you feel today?"
  - Set `greetingDone = true`
- [ ] Enable "Start Speaking" button only after greeting completes

---

## Phase 6: Polish & Production

### 6.1 Error Handling
- [ ] Handle WebSocket disconnection and reconnection
- [ ] Handle OpenAI API errors gracefully
- [ ] Handle HeyGen API errors gracefully
- [ ] Display user-friendly error messages

### 6.2 Session Cleanup
- [ ] Backend: Clean up OpenAI service on disconnect
- [ ] Backend: Close database connections properly
- [ ] Frontend: Stop audio tracks on unmount
- [ ] Frontend: Close WebSocket on unmount
- [ ] Frontend: Close HeyGen avatar session

### 6.3 Multi-User Support
- [ ] Verify session isolation (each user gets own OpenAI instance)
- [ ] Test concurrent sessions
- [ ] Monitor active sessions count

### 6.4 Configuration
- [ ] Environment-based API URLs (dev vs production)
- [ ] Configurable VAD settings
- [ ] Configurable system prompt
- [ ] Configurable avatar and voice

### 6.5 Testing
- [ ] Test single user flow end-to-end
- [ ] Test multiple concurrent users
- [ ] Test session cleanup on disconnect
- [ ] Test error recovery scenarios

---

## Implementation Order

For a working MVP, implement in this order:

1. **Backend OpenAI Service** - Core audio processing
2. **Backend WebSocket** - Connection handling
3. **Frontend WebSocket Hook** - Audio capture + streaming
4. **Basic UI** - Test audio flow works
5. **HeyGen Integration** - Add avatar
6. **Polish** - Greeting, error handling, cleanup

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Audio format | PCM16 @ 24kHz | OpenAI Realtime API requirement |
| TTS provider | HeyGen (not OpenAI) | Avatar lip-sync requires HeyGen TTS |
| Session management | Backend generates UUID | Ensures valid UUIDs, centralized control |
| Multi-user | Per-session service instances | Isolates state, prevents callback conflicts |
| VAD | Server-side (OpenAI) | Simplifies frontend, consistent behavior |

---

## Dependencies

### Backend
```
fastapi
uvicorn
websockets
python-dotenv
sqlalchemy
asyncpg
```

### Frontend
```
react
@heygen/streaming-avatar
```

### External Services
- OpenAI API (Realtime API access required)
- HeyGen API (Streaming Avatar access required)
- PostgreSQL database
