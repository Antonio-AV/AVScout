UV ?= uv

.PHONY: backend-install backend-dev backend-test data-acquire-wyscout frontend-dev frontend-build frontend-start frontend-test quality

backend-dev:
	$(UV) run --project backend --dev python backend/run.py

backend-test:
	$(UV) run --project backend --dev pytest backend/tests

data-acquire-wyscout:
	PYTHONPATH=backend $(UV) run --project backend --dev python -m app.data.acquire_wyscout

backend-install:
	$(UV) sync --project backend --dev

frontend-dev:
	npm run frontend:dev

frontend-build:
	npm run frontend:build

frontend-start:
	npm run frontend:start

frontend-test:
	npm run frontend:test

quality:
	npm run quality
