FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /workspace

RUN pip install --no-cache-dir uv==0.11.4

COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend --dev --frozen

CMD ["uv", "run", "--project", "backend", "--dev", "python", "backend/run.py"]
