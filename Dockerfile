FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim

WORKDIR /app
COPY --from=builder /install /usr/local

# Create non-root user
RUN useradd --create-home --shell /bin/bash tracker
USER tracker

# Data volume mount point
VOLUME /data

ENV TRACKER_DB=/data/tracker.db

ENTRYPOINT ["tracker"]
CMD ["fetch"]
