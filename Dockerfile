FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 oracle
WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
RUN pip install --no-cache-dir .
USER oracle
EXPOSE 8000
CMD ["uvicorn", "oracle_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
