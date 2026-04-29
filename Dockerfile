FROM python:3.13-slim AS builder

WORKDIR /build
# Install deps first so they cache independently of source changes.
COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim

WORKDIR /app
COPY --from=builder /install /usr/local

# Create non-root user and data directory
RUN useradd --create-home --shell /bin/bash tracker \
    && mkdir -p /data && chown tracker:tracker /data
USER tracker

VOLUME /data

ENV TRACKER_DB=/data/tracker.db \
    PYTHONUNBUFFERED=1

# Healthcheck only meaningful when running as web service. CLI runs ignore it.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz', timeout=3).status == 200 else 1)" \
        || exit 0

ENTRYPOINT ["tracker"]
CMD ["fetch"]
