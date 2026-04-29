# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.13-slim@sha256:a0779d7c12fc20be6ec6b4ddc901a4fd7657b8a6bc9def9d3fde89ed5efe0a3d

FROM ${PYTHON_IMAGE} AS builder

WORKDIR /build

# Copy only metadata first so the dependency install layer caches
# independently of source changes.
COPY pyproject.toml README.md ./

# Stub source tree so setuptools can resolve the package name during
# the deps-only install. Real source is copied in the next layer.
RUN mkdir -p src/anthropic_tracker && touch src/anthropic_tracker/__init__.py

# BuildKit cache mount: pip wheels persist across rebuilds in CI and locally.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install .

# Now copy real source and reinstall (only the package itself relayers,
# not its dependencies).
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install --no-deps --force-reinstall .

FROM ${PYTHON_IMAGE}

WORKDIR /app
COPY --from=builder /install /usr/local

# Pin UID so bind-mounts (if ever used) match host ownership predictably.
RUN useradd --create-home --uid 1000 --shell /bin/bash tracker \
    && mkdir -p /data && chown tracker:tracker /data
USER tracker

VOLUME /data

ENV TRACKER_DB=/data/tracker.db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# HEALTHCHECK is intentionally NOT defined here. It only makes sense for
# the long-running web service; CLI runs (fetch, dashboard, summary, etc.)
# would fail it. Healthcheck lives in docker-compose.yml on the web service.

ENTRYPOINT ["tracker"]
CMD ["fetch"]
