# Use Python 3.12 slim as the base image
FROM docker.io/python:3.12.5-slim-bookworm AS python

# Build stage for compiling dependencies and wheels
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=production

# Install necessary system dependencies for building Python packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential \
  libpq-dev \
  libsnappy-dev \
  gettext \
  binutils \
  libproj-dev \
  gdal-bin \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY ./requirements .

# Create wheels for faster installation during final stage
RUN pip wheel --wheel-dir /usr/src/app/wheels -r ${BUILD_ENVIRONMENT}.txt

# Production stage for final image setup
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Create a Django user and group for better security
RUN addgroup --system django && adduser --system --ingroup django django

# Install the necessary system dependencies in production
RUN apt-get update && apt-get install --no-install-recommends -y \
  libpq-dev \
  gettext \
  libsnappy-dev \
  binutils \
  libproj-dev \
  gdal-bin \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the wheels from the build stage
COPY --from=python-build-stage /usr/src/app/wheels /wheels/

# Install Python dependencies from the wheel cache
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* && rm -rf /wheels/

# Copy the application code into the Docker image
COPY --chown=django:django . ${APP_HOME}

# Set proper permissions for the application folder
RUN chown django:django ${APP_HOME}

# Ensure the entrypoint script has executable permissions
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the Django user to run the app
USER django

# Set the entrypoint script to execute on container start
CMD ["/entrypoint.sh"]
