# barbershopify — one-command dev workflow.
# `make setup` once, then `make dev` and open the printed URL.

BACKEND_PORT ?= 8731
PY := backend/.venv/bin/python

.PHONY: setup dev backend frontend test clean

setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .
	cd frontend && npm install

dev:
	@trap 'kill 0' EXIT; \
	(cd backend && .venv/bin/uvicorn app.main:app --port $(BACKEND_PORT) --reload) & \
	(cd frontend && npm run dev) & \
	wait

backend:
	cd backend && .venv/bin/uvicorn app.main:app --port $(BACKEND_PORT) --reload

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest

clean:
	rm -rf backend/.venv frontend/node_modules
