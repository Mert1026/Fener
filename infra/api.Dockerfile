FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.11.7
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY services ./services
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
RUN useradd --create-home --uid 10001 fener && mkdir -p /app/.data/snapshots && chown -R fener:fener /app/.data
USER fener
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "fener.api:app", "--host", "0.0.0.0", "--port", "8000"]
