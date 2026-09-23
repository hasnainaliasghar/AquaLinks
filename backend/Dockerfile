FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System libraries required by WeasyPrint, rasterio, and pyproj.
# `fonts-dejavu` + `fonts-liberation` give Pango a real serif / mono /
# sans family to fall back to — python:3.13-slim ships almost no fonts,
# so without these the PDF wordmark renders as empty space.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        libgdal-dev \
        gdal-bin \
        fonts-dejavu \
        fonts-liberation \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/data/uploads /app/data/reports

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/api/v1/health || exit 1

# Apply pending Alembic migrations on boot, then start the API.
# - ``PORT`` is set by Render's runtime; we default to 8000 for local
#   ``docker run`` parity.
# - ``exec`` makes uvicorn the PID-1 process so SIGTERM is forwarded
#   cleanly during deploys / scale-to-zero on the free tier.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
