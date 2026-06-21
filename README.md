# Automated Deck Generation System

A narrative verification engine generating boardroom-ready presentations from multi-source data.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

```bash
# Clone and start
git clone <repo-url>
cd bmad101
cp .env.example .env
docker-compose up
```

### Services

| Service    | URL                        | Description                    |
|------------|----------------------------|--------------------------------|
| Frontend   | http://localhost:3000       | React app (Vite dev server)    |
| Backend    | http://localhost:8000       | FastAPI (auto-docs at /docs)   |
| PostgreSQL | localhost:5432              | Database (deckgen/deckgen_dev) |
| Redis      | localhost:6379              | Cache                          |
| MinIO      | http://localhost:9000       | S3-compatible file storage     |
| MinIO Console | http://localhost:9001    | MinIO admin UI                 |

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Run Tests

```bash
# Backend unit tests
cd backend
pip install -r requirements.txt
pytest

# Integration smoke test (requires running containers)
bash scripts/smoke-test.sh
```

### Environment Variables

See `.env.example` for all configuration options.

## Project Structure

```
├── docker-compose.yml      # Service orchestration
├── backend/                # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/        # API endpoints
│   │   ├── core/          # Config, DB, Redis
│   │   └── models/        # SQLAlchemy models
│   ├── alembic/           # Database migrations
│   └── tests/             # pytest tests
├── frontend/              # React + Vite frontend
│   └── src/
│       ├── components/    # Reusable components
│       └── layouts/       # Page layouts
└── scripts/               # Utility scripts
```
