PYTHON ?= backend/.venv/bin/python

.PHONY: backend-dev backend-test frontend-dev frontend-build frontend-start frontend-test

backend-dev:
	$(PYTHON) backend/run.py

backend-test:
	$(PYTHON) -m pytest backend/tests

frontend-dev:
	npm run frontend:dev

frontend-build:
	npm run frontend:build

frontend-start:
	npm run frontend:start

frontend-test:
	npm run frontend:test
