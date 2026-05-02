# Brekora BMS

Booking Manager System — backend core.

## Prerequisites

- Docker Desktop
- Python 3.11+ (for local dev outside Docker)
- Git

## Quick Start

1. Clone the repository and navigate to the project root.

2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

3. Build and start the stack:
   ```bash
   docker compose up --build
   ```

4. Verify the API health endpoint:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

5. Open API docs in your browser:
   ```bash
   http://localhost:8000/docs
   ```

## Services

| Service | Image / Build           | Port | Purpose                |
|---------|------------------------|------|------------------------|
| api     | `python:3.11-slim`     | 8000 | FastAPI backend        |
| db      | `postgres:15-alpine` | 5432 | Primary database       |
| redis   | `redis:7-alpine`     | 6379 | Cache & task queue     |

## Development

- Hot reload is enabled for the FastAPI service. Changes to `backend/app/` are reflected immediately.
- All environment variables are defined in `.env` (created from `.env.example`).
- Never commit `.env` files containing secrets.

## Testing

Tests are located in `backend/tests/`. Run them from the `backend/` directory (pytest configuration is set up in task A-003).

```bash
cd backend
pytest
```
