# NexoPeople ATS (MVP)

Monorepo:
- backend: Django + DRF + CORS + SQLite
- frontend: Next.js + React + TypeScript + Tailwind

## Requirements
- Python 3.12+
- Node 20/22+
- Git

## Backend setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements/dev.txt
cp .env.example .env
