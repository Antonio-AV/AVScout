UV ?= uv

.PHONY: backend-install backend-dev backend-test frontend-dev frontend-build frontend-start frontend-test

backend-dev:
	$(UV) run --project backend --dev python backend/run.py

backend-test:
	$(UV) run --project backend --dev pytest backend/tests

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
