FROM postgres:16
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl nodejs python3 python3-venv \
    && python3 -m venv /opt/venv \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml alembic.ini ./
COPY backend ./backend
RUN --mount=type=cache,target=/root/.cache/pip pip install .
COPY migrations ./migrations
COPY templates ./templates
COPY frontend/dist ./frontend/dist
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    corepack enable \
    && corepack prepare pnpm@9.15.9 --activate \
    && cd templates/react-vite \
    && pnpm install --no-frozen-lockfile
RUN mkdir -p /app/artifacts /app/deployments
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
