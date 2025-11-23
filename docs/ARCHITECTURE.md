# Caresma Platform Architecture

This document describes the complete system architecture for the Caresma cognitive health assessment platform.

## System Overview

Caresma is a cognitive health assessment platform that enables:
- **Real-time voice conversations** with an AI-powered avatar
- **Cognitive assessment** across key domains (Memory, Language, Executive Function, Orientation)
- **Diagnostic-style reporting** with risk level indicators
- **Automated session scheduling** based on assessment severity
- **Calendar integration** for appointment management

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, HeyGen Streaming Avatar SDK, WebSocket |
| Backend | FastAPI (Python), AsyncIO, WebSockets |
| Database | PostgreSQL with SQLAlchemy ORM |
| AI Services | OpenAI Realtime API, OpenAI GPT-4 |
| Avatar | HeyGen Streaming Avatar (WebRTC) |
| Calendar | Google Calendar API / Outlook API |

---

## Complete Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      FRONTEND (React)                                             │
│                                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                                        App.js                                                │ │
│  │                           React Router: "/" and "/assessment"                                │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
│           │                                                      │                                │
│           ▼                                                      ▼                                │
│  ┌─────────────────────────────────┐                ┌─────────────────────────────────────────┐  │
│  │           Home.js               │                │        AssessmentView.js                │  │
│  │    (Interactive Session)        │                │     (Transcript Analysis)               │  │
│  │                                 │                │                                         │  │
│  │  • Start/End Session            │                │  • File upload (drag & drop)            │  │
│  │  • Microphone control           │                │  • Transcript validation                │  │
│  │  • Avatar greeting              │                │  • Submit for analysis                  │  │
│  │  • Status indicators            │                │                                         │  │
│  │  • Conversation display         │                └──────────────┬──────────────────────────┘  │
│  └────────────┬────────────────────┘                               │                              │
│               │                                                    ▼                              │
│               │                                    ┌─────────────────────────────────────────┐   │
│               │                                    │       AssessmentResults.js              │   │
│               │                                    │                                         │   │
│               │                                    │  • Overall score + risk badge           │   │
│               │                                    │  • Domain scores (visual bars)          │   │
│               │                                    │  • Recommendations                      │   │
│               │                                    │  • Scheduling options ◄─── NEW          │   │
│               │                                    │  • Print functionality                  │   │
│               │                                    └─────────────────────────────────────────┘   │
│               │                                                                                   │
│    ┌──────────┴────────────┬─────────────────────────────────────┐                               │
│    ▼                       ▼                                     ▼                               │
│  ┌─────────────────┐  ┌─────────────────────────┐  ┌───────────────────────────┐                │
│  │useOpenAIWebSocket│  │   useHeygenAvatar.js   │  │  assessmentService.js     │                │
│  │                 │  │                         │  │                           │                │
│  │• Record audio   │  │• StreamingAvatar SDK    │  │  POST /assessments/analyze│                │
│  │• PCM16 @ 24kHz  │  │• avatar.speak(text)     │  │  GET  /assessments/{id}   │                │
│  │• WS streaming   │  │• Video rendering        │  │  GET  /schedules          │◄─── NEW        │
│  └────────┬────────┘  └───────────┬─────────────┘  └─────────────┬─────────────┘                │
│           │                       │                              │                               │
└───────────┼───────────────────────┼──────────────────────────────┼───────────────────────────────┘
            │                       │                              │
            │ WebSocket             │ WebRTC                       │ REST API
            │ ws://                 │                              │ https://
            ▼                       ▼                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    BACKEND (FastAPI)                                               │
│                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    API Layer (app/api/v1/)                                   │  │
│  │                                                                                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │ websocket.py │  │assessments.py│  │ sessions.py  │  │ schedules.py │  │ calendar.py  │   │  │
│  │  │              │  │              │  │              │  │   ◄── NEW    │  │   ◄── NEW    │   │  │
│  │  │/ws/session/  │  │/assessments/ │  │ /sessions/   │  │ /schedules/  │  │ /calendar/   │   │  │
│  │  │   {id}       │  │   analyze    │  │              │  │              │  │   invites    │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │  │
│  └─────────┼─────────────────┼─────────────────┼─────────────────┼─────────────────┼───────────┘  │
│            │                 │                 │                 │                 │              │
│            ▼                 ▼                 ▼                 ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                   Service Layer (app/services/)                              │  │
│  │                                                                                              │  │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐ │  │
│  │  │ openai_service.py  │  │assessment_service.py│ │ schedule_service.py│  │calendar_service│ │  │
│  │  │                    │  │                    │  │                    │  │                │ │  │
│  │  │ • connect()        │  │ • analyze_transcript│ │                    │  │                │ │  │
│  │  │ • send_audio()     │  │ • calculate_scores │  │ • auto_schedule()  │  │ • create_event │ │  │
│  │  │ • _listen_from_llm │  │ • generate_report  │  │ • get_next_slot()  │  │ • send_invite  │ │  │
│  │  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘  └───────┬────────┘ │  │
│  │            │                       │                       │                     │          │  │
│  │            │                       ▼                       │                     │          │  │
│  │            │           ┌────────────────────────┐          │                     │          │  │
│  │            │           │ DiagnosticReportService│◄─────────┘                     │          │  │
│  │            │           │                        │                                │          │  │
│  │            │           │                        │────────────────────────────────┘          │  │
│  │            │           │ • summarize_pillars()  │                                           │  │
│  │            │           │ • determine_severity() │                                           │  │
│  │            │           │ • recommend_schedule() │                                           │  │
│  │            │           └────────────────────────┘                                           │  │
│  └────────────┼────────────────────────────────────────────────────────────────────────────────┘  │
│               │                                                                                    │
│               ▼                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    Model Layer (app/models/)                                 │  │
│  │                                                                                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐   │  │
│  │  │  User    │  │ Session  │  │ Message  │  │  Assessment  │  │ Schedule.                │   │  │
│  │  │          │  │          │  │          │  │              │  │                          │   │  │
│  │  │ id       │  │ id       │  │ id       │  │ id           │  │ id                       │   │  │
│  │  │ email    │◄─┤ user_id  │◄─┤session_id│  │ session_id   │  │ assessment_id            │   │  │
│  │  │ full_name│  │ status   │  │ role     │  │ *_score (x4) │  │ user_id                  │   │  │
│  │  │          │  │ started  │  │ content  │  │ *_feedback   │  │ scheduled_at             │   │  │
│  │  │          │  │ ended    │  │ encrypted│  │ risk_level   │  │ recurrence_rule          │   │  │
│  │  │          │  │          │  │          │  │ overall_*    │  │ calendar_event_id        │   │  │
│  │  │          │  │          │  │          │  │              │  │ status                   │   │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  └──────────────────────────┘   │  │
│  │       │              │             │              │                     │                   │  │
│  └───────┼──────────────┼─────────────┼──────────────┼─────────────────────┼───────────────────┘  │
│          └──────────────┴─────────────┴──────────────┴─────────────────────┘                      │
│                                              │                                                     │
│                                              ▼                                                     │
│                               ┌─────────────────────────────────┐                                 │
│                               │        PostgreSQL Database      │                                 │
│                               │                                 │                                 │
│                               │  Tables: users, sessions,       │                                 │
│                               │  messages, assessments,         │                                 │
│                               │  schedules                      │                                 │
│                               └─────────────────────────────────┘                                 │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
            │                                                                   │
            ▼                                                                   ▼
┌───────────────────────────────────────┐               ┌───────────────────────────────────────────┐
│        OpenAI Realtime API            │               │           External Services              │
│                                       │               │                                           │
│  • Speech-to-text (ASR)               │               │  ┌─────────────────────────────────────┐ │
│  • LLM response generation            │               │  │        HeyGen Cloud                 │ │
│  • Voice Activity Detection (VAD)     │               │  │  • Avatar rendering                 │ │
│                                       │               │  │  • Text-to-speech                   │ │
│  Events:                              │               │  │  • Video streaming (WebRTC)         │ │
│  • response.text.delta                │               │  └─────────────────────────────────────┘ │
│  • response.text.done                 │               │                                           │
│  • conversation.item                  |               |
    .input_audio_transcription.completed│               │  │   Google Calendar / Outlook API     │ │
│                                       │               │  │                                     │ │
└───────────────────────────────────────┘               │  │  • Create calendar events           │ │
                                                        │  │  • Send invites                     │ │
                                                        │  │  • Manage recurring appointments    │ │
                                                        │  └─────────────────────────────────────┘ │
                                                        └───────────────────────────────────────────┘
```