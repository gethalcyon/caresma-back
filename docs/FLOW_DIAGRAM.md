# Caresma System Flow Diagram

## Complete Audio-to-Avatar Flow

This document describes the complete flow from when a user speaks to when the AI avatar responds.

---

## 🎯 Key Features

### ✅ Automatic Voice Activity Detection (VAD)
The system uses **OpenAI's built-in VAD** to automatically detect when users stop speaking:
- **No button click required** - Just speak naturally and pause
- **500ms silence threshold** - Responds automatically after half-second pause
- **Configurable sensitivity** - Adjust detection threshold and silence duration
- **Manual override available** - "Stop Recording" button for immediate response

### 🔄 Dual Detection Modes
1. **Automatic (Default)** ⭐
   - OpenAI VAD monitors audio in real-time
   - Auto-commits after 500ms of silence
   - Natural conversation flow

2. **Manual (Override)**
   - User clicks "Stop Recording" button
   - Immediate response without waiting
   - User control when needed

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────┐          ┌──────────────────────┐               │
│  │  useOpenAIWebSocket│          │  useHeygenAvatar     │               │
│  │  Hook              │          │  Hook                │               │
│  └────────────────────┘          └──────────────────────┘               │
│           │                                 │                             │
│           │ WebSocket                       │ WebRTC                      │
└───────────┼─────────────────────────────────┼─────────────────────────────┘
            │                                 │
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌──────────────────────┐
│   BACKEND (FastAPI)   │         │   HeyGen Service     │
│   WebSocket Handler   │         │   (Cloud)            │
└───────────────────────┘         └──────────────────────┘
            │
            ▼
┌───────────────────────┐
│   OpenAI Realtime API │
│   (ASR + LLM)         │
└───────────────────────┘
```

---

## Detailed Flow: User Speaks → Avatar Responds

### Phase 1: Session Initialization

```
┌─────────┐                                  ┌──────────┐                 ┌─────────┐
│ Browser │                                  │ Backend  │                 │ HeyGen  │
└────┬────┘                                  └────┬─────┘                 └────┬────┘
     │                                            │                            │
     │ 1. POST /heygen/session-token             │                            │
     ├──────────────────────────────────────────►│                            │
     │                                            │                            │
     │                                            │ 2. Create token            │
     │                                            ├───────────────────────────►│
     │                                            │                            │
     │                                            │ 3. Return token            │
     │                                            │◄───────────────────────────┤
     │                                            │                            │
     │ 4. { token: "jwt..." }                    │                            │
     │◄───────────────────────────────────────────┤                            │
     │                                            │                            │
     │ 5. new StreamingAvatar({ token })          │                            │
     │────────────────────────────────────────────┼───────────────────────────►│
     │                                            │                            │
     │                                            │                            │
     │ 6. WebRTC connection established           │                            │
     │◄───────────────────────────────────────────┼────────────────────────────┤
     │    (video stream starts)                   │                            │
     │                                            │                            │
     │ 7. Connect WebSocket                       │                            │
     │    ws://backend/ws/session/{id}            │                            │
     ├──────────────────────────────────────────►│                            │
     │                                            │                            │
     │ 8. WebSocket connected                     │                            │
     │◄───────────────────────────────────────────┤                            │
     │                                            │                            │
```

### Phase 2: User Speaks - Audio Capture & Streaming

```
┌─────────┐                    ┌──────────┐                    ┌──────────┐
│ Browser │                    │ Backend  │                    │ OpenAI   │
│         │                    │ WebSocket│                    │ Realtime │
└────┬────┘                    └────┬─────┘                    └────┬─────┘
     │                              │                               │
     │ 1. User clicks                │                               │
     │    "Start Microphone"         │                               │
     ├─────────────────────         │                               │
     │                               │                               │
     │ 2. navigator.mediaDevices     │                               │
     │    .getUserMedia()            │                               │
     │    ✓ Get microphone access    │                               │
     │                               │                               │
     │ 3. Send JSON message          │                               │
     │    { type: "start_recording" }│                               │
     ├──────────────────────────────►│                               │
     │                               │                               │
     │                               │ 4. Backend marks              │
     │                               │    recording active           │
     │                               │                               │
     │ 5. Response                   │                               │
     │    { type: "recording_started"}│                               │
     │◄───────────────────────────────┤                               │
     │                               │                               │
     │                               │                               │
     │ 6. USER SPEAKS INTO MIC       │                               │
     │    🎤 Audio capture begins    │                               │
     │                               │                               │
     │ 7. ScriptProcessor captures   │                               │
     │    audio in 4096 sample chunks│                               │
     │    @ 24kHz sample rate        │                               │
     │                               │                               │
     │ 8. Convert Float32 → PCM16    │                               │
     │    (16-bit signed integers)   │                               │
     │                               │                               │
     │ 9. Send binary PCM16 data     │                               │
     │    <audio bytes> (every ~170ms)│                              │
     ├──────────────────────────────►│                               │
     │                               │                               │
     │                               │ 10. Accumulate audio          │
     │                               │     in buffer                 │
     │                               │                               │
     │                               │ 11. Forward to OpenAI         │
     │                               │     Realtime API              │
     │                               ├──────────────────────────────►│
     │                               │                               │
     │                               │                               │ 12. OpenAI streams
     │                               │                               │     partial transcripts
     │                               │                               │     (ASR in progress)
     │                               │                               │
```

### Phase 3: Stop Speaking Detection & Processing

**IMPORTANT: There are TWO ways the system detects when the user stops speaking:**

#### Option A: Automatic Voice Activity Detection (VAD) - DEFAULT BEHAVIOR ⭐

```
┌─────────┐                    ┌──────────┐                    ┌──────────┐
│ Browser │                    │ Backend  │                    │ OpenAI   │
└────┬────┘                    └────┬─────┘                    └────┬─────┘
     │                              │                               │
     │ 1. User is speaking           │                               │
     │    Audio streaming continues  │                               │
     │                               │                               │
     │                               │                               │ 2. OpenAI VAD monitors
     │                               │                               │    audio in real-time
     │                               │                               │
     │ 3. User stops speaking        │                               │
     │    (pauses/goes silent)       │                               │
     │                               │                               │
     │                               │                               │ 4. VAD detects silence
     │                               │                               │    for 500ms
     │                               │                               │    ⏱️  Threshold met!
     │                               │                               │
     │                               │                               │ 5. OpenAI AUTO-COMMITS
     │                               │                               │    audio buffer
     │                               │                               │    (no manual trigger!)
     │                               │                               │
     │                               │                               │ 6. OpenAI processes:
     │                               │                               │    - Finalize ASR
     │                               │                               │    - Run LLM
     │                               │                               │    - Generate response
     │                               │                               │
     │                               │ 7. Final transcript           │
     │                               │    "What's the weather?"      │
     │                               │◄───────────────────────────────┤
     │                               │                               │
     │ 8. Send transcript to UI      │                               │
     │    { type: "transcript",      │                               │
     │      text: "What's..." }      │                               │
     │◄───────────────────────────────┤                               │
     │                               │                               │
     │ 9. UPDATE UI:                 │                               │
     │    setUserTranscript(text)    │                               │
     │    ✅ "You: What's the        │                               │
     │        weather?"              │                               │
     │                               │                               │
```

**VAD Configuration (in backend):**
```python
# File: app/services/openai_service.py:307-312
"turn_detection": {
    "type": "server_vad",           # Server-side Voice Activity Detection
    "threshold": 0.5,                # Sensitivity (0.0-1.0)
    "prefix_padding_ms": 300,        # Include 300ms before speech
    "silence_duration_ms": 500       # Auto-commit after 500ms silence
}
```

#### Option B: Manual Stop Recording Button - OPTIONAL OVERRIDE

```
┌─────────┐                    ┌──────────┐                    ┌──────────┐
│ Browser │                    │ Backend  │                    │ OpenAI   │
└────┬────┘                    └────┬─────┘                    └────┬─────┘
     │                              │                               │
     │ 1. User clicks                │                               │
     │    "Stop Recording" button    │                               │
     │                               │                               │
     │ 2. stopRecording()            │                               │
     │    - Disconnect audio processor│                              │
     │    - Stop media tracks        │                               │
     │                               │                               │
     │ 3. Send JSON message          │                               │
     │    { type: "stop_recording" } │                               │
     ├──────────────────────────────►│                               │
     │                               │                               │
     │                               │ 4. Backend detects            │
     │                               │    "stop_recording"           │
     │                               │                               │
     │                               │ 5. Manual commit signal       │
     │                               │    to OpenAI (finalize)       │
     │                               ├──────────────────────────────►│
     │                               │    { type: "input_audio_      │
     │                               │      buffer.commit" }         │
     │                               │                               │
     │                               │                               │ 6. OpenAI processes:
     │                               │                               │    - Finalize ASR
     │                               │                               │    - Run LLM
     │                               │                               │    - Generate response
     │                               │                               │
     │                               │ 7. Final transcript           │
     │                               │◄───────────────────────────────┤
     │                               │                               │
     │ 8. Send transcript to UI      │                               │
     │◄───────────────────────────────┤                               │
     │                               │                               │
     │ 9. UPDATE UI                  │                               │
     │    ✅ Display transcript      │                               │
     │                               │                               │
```

**Code Locations:**
- Frontend click handler: [App.js:208-209](../src/App.js#L208-L209)
- Frontend stopRecording(): [useOpenAIWebSocket.js:157-180](../src/hooks/useOpenAIWebSocket.js#L157-L180)
- Backend handler: [websocket.py:117-121](../../caresma-backend/app/api/v1/websocket.py#L117-L121)
- Backend commit: [openai_service.py:123-147](../../caresma-backend/app/services/openai_service.py#L123-L147)

---

**KEY POINTS:**

1. **Default Behavior = Automatic VAD** ⭐
   - User speaks → pauses for 500ms → OpenAI auto-detects → response generated
   - No button click required!
   - More natural conversation flow

2. **Manual Button = Override**
   - User can click "Stop Recording" to force immediate response
   - Useful when user wants to respond before 500ms silence threshold
   - Bypasses VAD wait time

3. **When is transcript populated?**
   - Backend sends `{ type: "transcript", text: "..." }` after OpenAI processes speech
   - Frontend receives it at [useOpenAIWebSocket.js:46-48](../src/hooks/useOpenAIWebSocket.js#L46-L48)
   - Calls `setUserTranscript(text)` to update UI
   - Works the same for both VAD and manual stop

### Phase 4: AI Response Generation & Display

```
┌─────────┐                    ┌──────────┐                    ┌──────────┐
│ Browser │                    │ Backend  │                    │ OpenAI   │
└────┬────┘                    └────┬─────┘                    └────┬─────┘
     │                              │                               │
     │                              │ 1. OpenAI LLM generates       │
     │                              │    response text              │
     │                              │◄───────────────────────────────┤
     │                              │    "It's sunny and 72°F"      │
     │                              │                               │
     │ 2. Send AI response          │                               │
     │    { type: "text_response",  │                               │
     │      text: "It's sunny..." } │                               │
     │◄───────────────────────────────┤                               │
     │                              │                               │
     │ 3. UPDATE UI:                │                               │
     │    setAiResponse(text)       │                               │
     │    Display in conversation   │                               │
     │    ✅ "Assistant: It's       │                               │
     │        sunny and 72°F"       │                               │
     │                              │                               │
```

**KEY POINT - When is AI response populated?**
- AI response appears in the UI when backend sends `{ type: "text_response" }`
- Frontend receives it and calls `setAiResponse(text)`
- This happens at line 42-43 in useOpenAIWebSocket.js

### Phase 5: Avatar Speaks - Text to Video

```
┌─────────┐                                              ┌──────────┐
│ Browser │                                              │ HeyGen   │
│         │                                              │ Service  │
└────┬────┘                                              └────┬─────┘
     │                                                        │
     │ 1. Receive text_response                              │
     │    (from Phase 4)                                     │
     │                                                        │
     │ 2. onTextResponseRef callback                         │
     │    triggered in App.js (line 39-44)                   │
     │                                                        │
     │ 3. Call speak(text)                                   │
     │    from useHeygenAvatar hook                          │
     │                                                        │
     │ 4. avatarRef.current.speak({                          │
     │      text: "It's sunny and 72°F",                     │
     │      taskType: "repeat"                               │
     │    })                                                 │
     │                                                        │
     │ 5. HeyGen SDK sends text                              │
     │    via WebRTC data channel                            │
     ├───────────────────────────────────────────────────────►│
     │                                                        │
     │                                                        │ 6. HeyGen:
     │                                                        │    - Text-to-Speech
     │                                                        │    - Lip sync generation
     │                                                        │    - Avatar video render
     │                                                        │
     │ 7. Stream video frames back                           │
     │    via WebRTC (H.264)                                 │
     │◄───────────────────────────────────────────────────────┤
     │                                                        │
     │ 8. Video element displays                             │
     │    avatar speaking the text                           │
     │    🎬 Avatar lips move!                               │
     │                                                        │
     │ 9. Event: AVATAR_START_TALKING                        │
     │    setIsSpeaking(true)                                │
     │    ✅ Status: "Avatar is speaking..."                 │
     │                                                        │
     │ 10. Event: AVATAR_STOP_TALKING                        │
     │     setIsSpeaking(false)                              │
     │     ✅ Status: "Ready"                                │
     │                                                        │
```

---

## How Backend Detects "User Stopped Speaking"

**✅ AUTOMATIC DETECTION IS ENABLED** - The system uses OpenAI's built-in Voice Activity Detection (VAD).

### Method 1: Automatic VAD (Default - ENABLED ⭐)

```javascript
User speaks → pauses for 500ms
  ↓
OpenAI VAD automatically detects silence
  ↓
OpenAI auto-commits audio buffer (no manual trigger!)
  ↓
OpenAI processes → sends transcript & response to backend
  ↓
Backend forwards to frontend → UI updates
```

**Configuration:** [openai_service.py:307-312](../../caresma-backend/app/services/openai_service.py#L307-L312)
```python
"turn_detection": {
    "type": "server_vad",           # ✅ Server-side VAD enabled
    "threshold": 0.5,                # Sensitivity (0.0-1.0)
    "prefix_padding_ms": 300,        # Include 300ms before speech
    "silence_duration_ms": 500       # ⏱️  Auto-commit after 500ms silence
}
```

**How it works:**
1. OpenAI monitors audio stream in real-time
2. Detects when user stops speaking (500ms silence)
3. Automatically commits audio buffer
4. Processes ASR + LLM
5. Sends results back to backend

### Method 2: Manual Control (Optional Override)

```javascript
// User can manually force response by clicking button
stopRecording()  // User clicks "Stop Recording" button
  ↓
ws.send({ type: "stop_recording" })
  ↓
Backend receives signal → commits audio → OpenAI processes
```

**When to use manual control:**
- User wants immediate response (don't wait for 500ms)
- User finished speaking but hasn't paused long enough
- Override VAD automatic detection

---

**Current System:** Uses **both** methods:
- **Primary:** Automatic VAD detection (500ms silence threshold)
- **Backup:** Manual "Stop Recording" button for user override
- This provides the best of both worlds: natural conversation + user control

---

## Timeline of State Changes

### User Transcript Population

#### With Automatic VAD (Default):

```
Timeline:
─────────────────────────────────────────────────────────────────────►
                                                                   time

User starts speaking       User stops speaking      Transcript appears in UI
        │                   (500ms silence)                   │
        │   Recording active    │   VAD auto-detects         │
        ├───────────────────────┤───────────────────────────►│
        │   Audio streaming     │   OpenAI processes         │
        │                       │                            │
        ▼                       ▼                            ▼
   isRecording=true      OpenAI VAD triggers       userTranscript = "..."
                         (automatic)                ✅ Displayed in UI
```

**Key Point:** With VAD, there's a delay of ~0.5-2 seconds:
- User pauses for 500ms
- OpenAI VAD auto-detects silence
- OpenAI processes audio
- Transcript appears in frontend UI

#### With Manual Button:

```
Timeline:
─────────────────────────────────────────────────────────────────────►
                                                                   time

User starts speaking          User clicks stop           Transcript appears in UI
        │                            │                            │
        │   Recording active         │   Manual commit           │
        ├────────────────────────────┤──────────────────────────►│
        │   Audio streaming          │   OpenAI processes        │
        │                            │                            │
        ▼                            ▼                            ▼
   isRecording=true           isRecording=false          userTranscript = "..."
                                                         ✅ Displayed in UI
```

**Key Point:** Manual control bypasses 500ms wait but adds UI interaction time

### AI Response Population

```
Timeline:
─────────────────────────────────────────────────────────────────────►
                                                                   time

Transcript received        OpenAI LLM thinks           AI response appears
        │                         │                            │
        │   Backend processes     │   Response generated       │
        ├─────────────────────────┤───────────────────────────►│
        │   GPT-4 generation      │                            │
        │                         │                            │
        ▼                         ▼                            ▼
   status: "Processing..."   Generating response...    aiResponse = "..."
                                                        ✅ Displayed in UI
```

**Key Point:** AI response typically takes 1-5 seconds to generate, depending on:
- Length of user input
- Complexity of response
- OpenAI API latency

### Avatar Speaking

```
Timeline:
─────────────────────────────────────────────────────────────────────►
                                                                   time

AI response received       HeyGen processes           Avatar speaks
        │                         │                         │
        │   speak(text) called    │   TTS + lip sync       │
        ├─────────────────────────┤────────────────────────►│
        │   HeyGen API call       │   Video generation      │
        │                         │                         │
        ▼                         ▼                         ▼
   Send text to HeyGen       Processing...         isSpeaking = true
                                                    🎬 Video plays

                                                    Avatar finishes
                                                          │
                                                          ▼
                                                    isSpeaking = false
```

**Key Point:** There's a delay of ~500ms-2s between:
- Frontend calls `speak(text)`
- Avatar starts visibly speaking (lips moving)

---

## Data Formats

### Audio Format (Frontend → Backend)
```
Format: PCM16 (signed 16-bit integers)
Sample Rate: 24,000 Hz (24 kHz)
Channels: 1 (mono)
Chunk Size: 4096 samples (~170ms of audio)
Byte Size: 8192 bytes per chunk (4096 samples × 2 bytes)
Transport: Binary WebSocket frames
```

### WebSocket Messages

#### Frontend → Backend
```typescript
// JSON Messages
{ type: "start_recording" }
{ type: "stop_recording" }
{ type: "ping" }

// Binary Messages
<PCM16 audio bytes>
```

#### Backend → Frontend
```typescript
// Status updates
{ type: "recording_started" }
{ type: "recording_stopped" }
{ type: "pong" }

// Transcription
{
  type: "transcript",
  text: "What's the weather like?"
}

// AI Response
{
  type: "text_response",
  text: "It's sunny and 72 degrees."
}

// Errors
{
  type: "error",
  message: "Connection failed"
}
```

---

## Key Components & Responsibilities

### Frontend

#### `useOpenAIWebSocket` Hook
**Responsibilities:**
- Establish WebSocket connection to backend
- Capture microphone audio
- Convert audio to PCM16 format
- Stream audio chunks to backend
- Receive transcripts and AI responses
- Manage recording state

**Key Functions:**
- `startRecording()` - Start audio capture
- `stopRecording()` - Stop audio capture
- `setOnTextResponse(callback)` - Register AI response handler
- `setOnTranscript(callback)` - Register transcript handler

#### `useHeygenAvatar` Hook
**Responsibilities:**
- Get session token from backend
- Initialize HeyGen Streaming Avatar SDK
- Establish WebRTC connection to HeyGen
- Receive avatar video stream
- Control avatar speech
- Track avatar speaking state

**Key Functions:**
- `speak(text)` - Make avatar speak text
- `stopSpeaking()` - Interrupt avatar
- `closeAvatar()` - End avatar session

#### `App.js`
**Responsibilities:**
- Coordinate between audio and avatar
- Display conversation UI
- Handle user interactions
- Manage session lifecycle

**Key State:**
- `sessionStarted` - Whether session is active
- `userTranscript` - User's speech (populated after stop recording)
- `aiResponse` - AI's text response (populated when received)
- `isRecording` - Whether actively recording audio
- `isSpeaking` - Whether avatar is speaking

### Backend

#### WebSocket Handler (`/ws/session/{session_id}`)
**Responsibilities:**
- Accept WebSocket connections
- Receive audio chunks from frontend
- Buffer audio data
- Connect to OpenAI Realtime API
- Forward audio to OpenAI
- Receive transcripts and responses from OpenAI
- Send transcripts and responses to frontend

**Key Events Handled:**
- `start_recording` - Start audio session
- `stop_recording` - Finalize audio, trigger processing
- Binary frames - Audio data

#### HeyGen Token Service (`/heygen/session-token`)
**Responsibilities:**
- Create HeyGen session tokens
- Secure token generation
- Return token to frontend

---

## Error Handling

### Connection Errors
```
Frontend detects:
- WebSocket disconnect
- Avatar stream disconnect
- Microphone permission denied

Actions:
- Display error message
- Allow retry
- Clean up resources
```

### Audio Errors
```
Backend detects:
- OpenAI API errors
- Invalid audio format
- Timeout

Actions:
- Send error message to frontend
- Log error details
- Reset session state
```

---

## Performance Considerations

### Latency Breakdown
```
User stops speaking
  ↓ ~100ms - Network transit
Backend receives stop signal
  ↓ ~500ms - OpenAI ASR finalization
Transcript generated
  ↓ ~50ms - Network transit
Frontend displays transcript
  ↓ ~2000ms - OpenAI LLM generation
AI response generated
  ↓ ~50ms - Network transit
Frontend receives response
  ↓ ~100ms - speak() call
HeyGen receives text
  ↓ ~1000ms - TTS + lip sync
Avatar starts speaking
──────────────────────────
Total: ~3.8 seconds (typical)
```

### Optimization Opportunities
1. **Reduce OpenAI latency** - Use streaming responses
2. **Pre-warm HeyGen** - Keep session alive
3. **Use VAD** - Auto-detect speech end
4. **Optimize audio chunks** - Smaller chunks = faster processing
5. **Parallel processing** - Start LLM while finalizing ASR

---

## Summary

### Complete Flow in Simple Terms:

1. **User clicks "Start Session"**
   - Frontend gets HeyGen token from backend
   - Frontend connects to HeyGen (WebRTC video starts)
   - Frontend connects to backend (WebSocket opens)

2. **User clicks "Start Microphone"**
   - Browser asks for microphone permission
   - Audio capture begins (24kHz, PCM16)
   - Audio streams to backend every ~170ms

3. **User speaks**
   - Audio continuously streams
   - Backend forwards to OpenAI
   - OpenAI VAD monitors for silence in real-time

4. **User stops speaking (pauses for 500ms) OR clicks "Stop Recording"**
   - **Automatic (VAD):** OpenAI detects 500ms silence and auto-commits
   - **Manual:** User clicks button, backend sends commit signal
   - OpenAI generates final transcript
   - **Transcript appears in UI** ← This is when userTranscript is populated

5. **OpenAI generates response**
   - Backend sends to frontend
   - **AI response appears in UI** ← This is when aiResponse is populated
   - Frontend calls `speak(text)` on HeyGen avatar

6. **Avatar speaks**
   - HeyGen converts text to speech + video
   - Video streams back via WebRTC
   - Avatar lips move, user sees response

---

## FAQ

**Q: When exactly does the user transcript appear?**
A: After the user stops speaking for 500ms (VAD auto-detects) OR clicks "Stop Recording", OpenAI processes the audio and sends the final transcript back. This takes ~0.5-2 seconds with VAD, ~1-3 seconds with manual stop.

**Q: How does the backend know the user stopped speaking?**
A: **Two ways:**
1. **Automatic (Default):** OpenAI Realtime API has built-in Voice Activity Detection (VAD) that monitors audio and auto-detects 500ms of silence
2. **Manual (Override):** User clicks "Stop Recording" button, frontend sends `{ type: "stop_recording" }` to backend

**Q: Can we adjust the VAD sensitivity?**
A: Yes! Edit the configuration in [openai_service.py:307-312](../../caresma-backend/app/services/openai_service.py#L307-L312):
```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,              # ← Adjust 0.0-1.0 (lower = more sensitive)
    "silence_duration_ms": 500     # ← Change milliseconds (300-1500 recommended)
}
```

**Q: Why is there a delay before the avatar speaks?**
A: Multiple steps: OpenAI ASR (500ms) → OpenAI LLM (2s) → Network (50ms) → HeyGen TTS+lipsync (1s) = ~3.5 seconds total.

**Q: Does the video come from the backend?**
A: No! Video comes directly from HeyGen to the browser via WebRTC. Backend only handles audio/text. This keeps video quality high and latency low.

---

## Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (Browser)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Video       │  │ Conversation │  │  Controls    │                  │
│  │  (Avatar)    │  │  Display     │  │  (Buttons)   │                  │
│  │              │  │              │  │              │                  │
│  │  - Shows     │  │ - User text  │  │ - Start Mic  │                  │
│  │    HeyGen    │  │ - AI text    │  │ - Stop Mic   │                  │
│  │    avatar    │  │              │  │ - End Session│                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                 │                  │                           │
└─────────┼─────────────────┼──────────────────┼───────────────────────────┘
          │                 │                  │
          │ WebRTC          │ State Updates    │ Events
          │ (video)         │ (text)           │ (clicks)
          │                 │                  │
          │                 ▼                  │
          │         ┌────────────────┐         │
          │         │   App.js       │◄────────┘
          │         │   (Coordinator)│
          │         └───────┬────────┘
          │                 │
          │                 ├──────────────────┬──────────────────┐
          │                 ▼                  ▼                  ▼
          │         ┌────────────────┐  ┌──────────────┐  ┌──────────────┐
          │         │useHeygenAvatar │  │useOpenAI     │  │   State      │
          │         │                │  │WebSocket     │  │   Variables  │
          │         └───────┬────────┘  └──────┬───────┘  └──────────────┘
          │                 │                  │
          └─────────────────┘                  │
                    │                          │
                    │ WebRTC                   │ WebSocket
                    │                          │
                    ▼                          ▼
          ┌─────────────────┐        ┌─────────────────┐
          │  HeyGen Cloud   │        │  Backend        │
          │  Service        │        │  (FastAPI)      │
          │                 │        │                 │
          │  - TTS          │        │  - Audio buffer │
          │  - Lip sync     │        │  - WebSocket    │
          │  - Video render │        │    handler      │
          └─────────────────┘        └────────┬────────┘
                                               │
                                               │ HTTP API
                                               │
                                               ▼
                                     ┌─────────────────┐
                                     │  OpenAI         │
                                     │  Realtime API   │
                                     │                 │
                                     │  - ASR (Speech  │
                                     │    to Text)     │
                                     │  - LLM (GPT-4)  │
                                     │  - VAD (Voice   │
                                     │    Activity     │
                                     │    Detection)   │
                                     └─────────────────┘
```

---

## Quick Reference: VAD Configuration

### Current Settings (Production)
```python
# File: app/services/openai_service.py:307-312
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,
    "prefix_padding_ms": 300,
    "silence_duration_ms": 500
}
```

### Recommended Settings by Use Case

| Use Case | `silence_duration_ms` | `threshold` | Description |
|----------|----------------------|-------------|-------------|
| **Fast Chat** | 300-400ms | 0.4-0.5 | Quick responses, may cut off slower speakers |
| **Natural Conversation** ⭐ | 500-700ms | 0.5-0.6 | Balanced, good for most users (current) |
| **Careful Listening** | 800-1200ms | 0.6-0.7 | Patient, allows longer pauses |
| **Noisy Environment** | 600-800ms | 0.7-0.8 | Less sensitive, reduces false triggers |

### How to Change Settings

1. Edit [app/services/openai_service.py:307-312](../../caresma-backend/app/services/openai_service.py#L307-L312)
2. Adjust `silence_duration_ms` (recommended: 300-1500ms)
3. Adjust `threshold` (0.0 = very sensitive, 1.0 = less sensitive)
4. Restart backend server
5. Test with real users

### Troubleshooting

**Problem: System responds too quickly (cuts off user)**
- ✅ Increase `silence_duration_ms` to 700-1000ms
- ✅ Decrease `threshold` to 0.4-0.5 (less sensitive)

**Problem: System takes too long to respond**
- ✅ Decrease `silence_duration_ms` to 300-400ms
- ✅ Increase `threshold` to 0.6-0.7 (more sensitive)

**Problem: False triggers in noisy environment**
- ✅ Increase `threshold` to 0.7-0.8
- ✅ Keep `silence_duration_ms` at 500-700ms

---

## Technology Stack

### Frontend
- **React** - UI framework
- **@heygen/streaming-avatar** - Avatar video/TTS
- **WebSocket** - Real-time audio streaming
- **Web Audio API** - Microphone capture

### Backend
- **FastAPI** - Python web framework
- **WebSocket** - Real-time communication
- **OpenAI Realtime API** - ASR + LLM + VAD

### External Services
- **OpenAI** - Speech recognition, language model, voice activity detection
- **HeyGen** - Avatar rendering, lip-sync, video streaming

