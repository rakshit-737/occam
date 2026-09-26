FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY occam ./occam
COPY fixtures ./fixtures
RUN pip install --no-cache-dir ".[api,stix,graph]" \
 && useradd --create-home --uid 10001 occam
USER occam

ENV OCCAM_FIXTURES=/app/fixtures
EXPOSE 8000
CMD ["uvicorn", "occam.api:app", "--host", "0.0.0.0", "--port", "8000"]
