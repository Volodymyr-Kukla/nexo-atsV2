.PHONY: backend-install frontend-install backend-lint frontend-lint

backend-install:
	cd backend && python -m venv .venv || true
	cd backend && . .venv/bin/activate && pip install -r requirements/dev.txt

backend-lint:
	cd backend && . .venv/bin/activate && ruff check .
	cd backend && . .venv/bin/activate && black --check .
	cd backend && . .venv/bin/activate && isort --check-only .

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run lint
