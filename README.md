# Caresma Backend

A modern FastAPI backend application with clean architecture.

## Features

- FastAPI framework
- Async SQLAlchemy with PostgreSQL
- JWT authentication
- Clean architecture (repositories, services, routers)
- Alembic migrations
- Pydantic models for validation
- CORS middleware

## Project Structure

```
app/
├── api/                  # API endpoints
│   └── v1/              # API version 1
│       ├── users.py
│       ├── auth.py
│       └── sessions.py
├── core/                # Core configuration
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── events.py
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── services/            # Business logic
├── repositories/        # Database operations
├── db/                  # Database configuration
├── workers/             # Background tasks
└── utils/               # Utilities
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .
```

Or install with development dependencies:
```bash
pip install -e ".[dev]"
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Update the `.env` file with your configuration.

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Running Tests
First install dev dependencies:
```bash
pip install -e ".[dev]"
```

Then run tests:
```bash
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

### Type Checking
```bash
mypy app
```

### Creating a New Migration
```bash
alembic revision --autogenerate -m "description"
```

### Applying Migrations
```bash
alembic upgrade head
```

## License

MIT
