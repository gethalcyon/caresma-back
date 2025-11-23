# Caresma Backend

A FastAPI backend for the Caresma cognitive health assessment platform. Provides real-time voice conversations with AI, cognitive assessments, and session management.

## Features

- **Real-time Voice Chat**: WebSocket-based audio streaming with OpenAI Realtime API
- **Cognitive Assessments**: AI-powered analysis across Memory, Language, Executive Function, and Orientation
- **HeyGen Integration**: Avatar session token management
- **Message Encryption**: All conversation messages encrypted at rest
- **Session Management**: Multi-user session support with UUID-based tracking
- **PostgreSQL Database**: Async SQLAlchemy with Alembic migrations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (app/api/v1/)                                        │
│  ├── websocket.py      - Real-time audio streaming              │
│  ├── assessments.py    - Cognitive assessment endpoints         │
│  ├── sessions.py       - Session management                     │
│  └── heygen.py         - Avatar token management                │
├─────────────────────────────────────────────────────────────────┤
│  Service Layer (app/services/)                                  │
│  ├── openai_service.py      - OpenAI Realtime API client        │
│  ├── assessment_service.py  - Assessment analysis logic         │
│  └── message_service.py     - Message persistence               │
├─────────────────────────────────────────────────────────────────┤
│  Model Layer (app/models/)                                      │
│  ├── user.py, session.py, message.py, assessment.py            │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- OpenAI API key (with Realtime API access)
- HeyGen API key

## Quick Start

### 1. Clone and Setup Environment

```bash
cd caresma-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/caresma

# Security
SECRET_KEY=your-secret-key-here

# OpenAI (Required for voice chat)
OPENAI_API_KEY=sk-...

# HeyGen (Required for avatar)
HEYGEN_API_KEY=your-heygen-api-key

# Encryption (for message encryption)
ENCRYPTION_KEY=your-32-byte-encryption-key
```

### 3. Setup Database

```bash
# Create database
createdb caresma

# Run migrations
alembic upgrade head
```

### 4. Start the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### WebSocket - Real-time Voice Chat
```
WS  /api/v1/ws/session/{session_id}   - Audio streaming endpoint
```

### Assessments
```
POST   /api/v1/assessments/analyze       - Analyze transcript text
POST   /api/v1/assessments/analyze-file  - Upload and analyze file
GET    /api/v1/assessments/{id}          - Get assessment by ID
GET    /api/v1/assessments/session/{id}  - Get all session assessments
DELETE /api/v1/assessments/{id}          - Delete assessment
```

### Sessions
```
POST   /api/v1/sessions                  - Create new session
GET    /api/v1/sessions/{id}             - Get session details
GET    /api/v1/sessions/{id}/messages    - Get session messages
```

### HeyGen
```
POST   /api/v1/heygen/session-token      - Get avatar streaming token
POST   /api/v1/heygen/cleanup-sessions   - Cleanup abandoned sessions
```

## API Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
app/
├── api/
│   └── v1/
│       ├── websocket.py       # WebSocket for audio streaming
│       ├── assessments.py     # Assessment endpoints
│       ├── sessions.py        # Session management
│       ├── heygen.py          # HeyGen token management
│       ├── auth.py            # Authentication
│       └── users.py           # User management
├── core/
│   ├── config.py              # Settings and configuration
│   ├── security.py            # Auth and encryption
│   ├── encryption.py          # Message encryption service
│   └── logging.py             # Logging configuration
├── models/
│   ├── user.py                # User model
│   ├── session.py             # Session model
│   ├── message.py             # Message model (encrypted)
│   └── assessment.py          # Assessment model
├── schemas/                   # Pydantic schemas
├── services/
│   ├── openai_service.py      # OpenAI Realtime API client
│   ├── assessment_service.py  # Assessment logic
│   └── message_service.py     # Message persistence
├── db/
│   ├── base.py                # SQLAlchemy base
│   └── session.py             # Database session
└── main.py                    # Application entry point
```

## Development

### Running Tests
```bash
pip install -e ".[dev]"
pytest
```

### Code Formatting
```bash
black .
```

### Linting
```bash
ruff check .
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## WebSocket Protocol

### Client to Server

**Audio data (binary)**: PCM16 audio at 24kHz, mono

**Control messages (JSON)**:
```json
{"type": "start_recording"}
{"type": "stop_recording"}
{"type": "ping"}
```

### Server to Client

```json
{"type": "session_created", "session_id": "uuid"}
{"type": "transcript", "text": "user speech"}
{"type": "text_response", "text": "AI response"}
{"type": "recording_started"}
{"type": "recording_stopped"}
{"type": "error", "message": "error details"}
{"type": "pong"}
```

## Documentation

See the `docs/` folder for detailed documentation:
- `ARCHITECTURE.md` system architecture
- `ARCHITECTURE-NEXT-STEPS.md` - Full projected system architecture
- `FLOW_DIAGRAM.md` - Data flow diagrams
- `IMPROVEMENTS.md` - Next steps

## License

MIT
