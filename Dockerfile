FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY occam ./occam

RUN pip install --no-cache-dir ".[api,stix,graph]" \
 && useradd --create-home --uid 10001 occam
USER 10001:10001

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
# 0.0.0.0 inside the container only; publish it on loopback: docker run -p 127.0.0.1:8000:8000 ...
CMD ["uvicorn", "occam.api:app", "--host", "0.0.0.0", "--port", "8000"]
