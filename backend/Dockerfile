FROM python:3.12-slim-bookworm AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt
FROM python:3.12-slim-bookworm AS runtime
ARG VERSION=development
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_VERSION=$VERSION
RUN groupadd --gid 10001 stockpilot && useradd --uid 10001 --gid stockpilot --no-create-home stockpilot
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 . .
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health',timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
