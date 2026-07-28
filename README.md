# AVScout

AVScout is a local, bilingual scouting workspace for explainable historical player
recommendations. The repository is split into a Python API and a Next.js web app.

## Requirements

- Python 3.11 or newer
- uv 0.11 or newer
- Node.js 20.9 or newer
- npm 10 or newer

## Quick start

From the repository root:

```bash
cp .env.example .env
uv sync --project backend --dev
npm install
```

The environment file contains optional placeholders only. Keep real credentials in
`.env`, which is ignored by Git. The API currently starts without an OpenAI key;
the key will be used by the query and explanation features added later.

Start the applications in separate terminals:

```bash
uv run --project backend --dev python backend/run.py
npm run frontend:dev
```

The API is available at `http://localhost:8000` and the web app at
`http://localhost:3000`. The API health check is available at
`http://localhost:8000/health`.

## Tests

```bash
uv run --project backend --dev pytest backend/tests
npm run frontend:test
```

The backend environment can also be synchronized with `make backend-install`.
The test commands are available through `make backend-test` and
`make frontend-test` when GNU Make is installed.

## Repository layout

```text
backend/    FastAPI application and Python tests
frontend/   Next.js application and frontend smoke tests
```

Raw downloads, generated analytical data, dependency folders, local databases,
secrets, and test artifacts are excluded from source control. Data acquisition and
processing commands will be added with the data pipeline work.
