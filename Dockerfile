# Use a consistent base image and force AMD64 architecture (Render is x86_64)
FROM --platform=linux/amd64 python:3.12.5-slim-bookworm AS base

# ─────────────────────────────────────────────────────────────
# 1️⃣ Build stage — create dependency wheels
# ─────────────────────────────────────────────────────────────
FROM base AS build

ARG BUILD_ENVIRONMENT=production

# Install build dependencies (for compiling Python packages)
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ./requirements ./requirements

# Build dependency wheels
RUN pip wheel --wheel-dir /usr/src/app/wheels -r ${BUILD_ENVIRONMENT}.txt


# ─────────────────────────────────────────────────────────────
# 2️⃣ Runtime stage — minimal image for running Django
# ─────────────────────────────────────────────────────────────
FROM base AS runtime

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BUILD_ENV=${BUILD_ENVIRONMENT} \
    PATH="/home/django/.local/bin:$PATH"

WORKDIR ${APP_HOME}

# Create non-root user
RUN addgroup --system django && adduser --system --ingroup django django

# Install runtime dependencies only
RUN apt-get update && apt-get install --no-install-recommends -y \
    bash \
    libpq-dev \
    gettext \
    libsnappy-dev \
    binutils \
    libproj-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy built dependency wheels and install them
COPY --from=build /usr/src/app/wheels /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && rm -rf /wheels

# Copy project code
COPY --chown=django:django . ${APP_HOME}

# Copy entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Make sure bash is used as the default shell for scripts
SHELL ["/bin/bash", "-c"]

# Switch to non-root user
USER django

# Default command
ENTRYPOINT ["/entrypoint.sh"]
