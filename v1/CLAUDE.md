# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AppQueue (QXpert) is a clinical laboratory queue management system with a FastAPI backend and Angular 18 frontend. It handles patient queuing, ticket generation, workstation management, and real-time notifications via WebSocket.

## Development Commands

### Backend (Python/FastAPI)
```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server (with hot reload)
python run_dev.py
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run tests by marker
pytest -m unit
pytest -m integration

# Code formatting and linting
black app/
flake8 app/
mypy app/
```

### Frontend (Angular)
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm start
# OR
ng serve --host 0.0.0.0 --port 4200

# Build for production
npm run build

# Run tests
npm test
```

### Docker Development
```bash
# From project root (parent of v1/)
docker-compose -f docker-compose.dev.yml up
```

## Architecture

### Backend Layers (`backend/app/`)
- **api/v1/endpoints/**: REST API endpoints (auth, tickets, queue, patients, stations, users, service_types, websocket, admin)
- **services/**: Business logic layer (queue_service, station_service, auth_service, notification_service)
- **crud/**: Database access operations with generic base class in `crud/base.py`
- **models/**: SQLAlchemy ORM models (SQL Server)
- **schemas/**: Pydantic validation models
- **core/**: Configuration (`config.py`), database (`database.py`), Redis (`redis.py`), security (`security.py`)

### Frontend Structure (`frontend/src/app/`)
- **components/**: Standalone Angular 18 components (no NgModules)
- **services/**: HTTP services and state management with RxJS
- Angular Material with Azure Blue theme
- Route guards: AuthGuard, RoleGuard, AdminGuard, SupervisorGuard

### API Routes
All API endpoints are prefixed with `/api/v1/`:
- `/auth` - Authentication (JWT)
- `/tickets` - Ticket generation with QR codes
- `/queue` - Queue state management
- `/patients` - Patient management
- `/stations` - Workstation control
- `/users` - User management
- `/service-types` - Service categories
- `/admin` - Administrative operations
- `/ws` - WebSocket for real-time updates

### Database & Cache
- **SQL Server** via SQLAlchemy + pyodbc (ODBC Driver 17)
- **Redis** for caching and real-time state
- Alembic for migrations (`backend/alembic/`)

## Key Configuration

### Environment Variables (`.env`)
Required variables:
- `DB_SERVER`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD` - SQL Server connection
- `REDIS_HOST`, `REDIS_PORT` - Redis connection
- `SECRET_KEY` - JWT signing key
- `ALLOWED_ORIGINS` - CORS origins (comma-separated)

Settings loaded via Pydantic in `backend/app/core/config.py`.

### Frontend API URL
Configure in `frontend/src/app/environments/` for different environments.

## Role-Based Access
User roles: Admin, Supervisor, Técnico, Enfermero, Doctor, Recepcionista

Route protection in frontend via guards, backend via dependency injection in `api/dependencies/permissions.py`.

## Real-time Features
WebSocket endpoints in `api/v1/endpoints/websocket.py` handle live queue updates and display notifications.
