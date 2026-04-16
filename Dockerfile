# syntax=docker/dockerfile:1

# python:3.12-slim is a minimal Debian-based Linux image with Python 3.12 pre-installed.
# "slim" strips out compilers and extra tools to keep the image small.
FROM python:3.12-slim

# Install the packages needed to add Microsoft's apt repository:
#   - curl: download the Microsoft signing key
#   - gnupg: verify the key signature
#   - apt-transport-https: allow apt to fetch packages over HTTPS
# Then clean up the apt cache to keep the image layer small.
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft's package signing key and apt repository for SQL Server ODBC drivers.
# This is the Linux equivalent of what Homebrew did on your Mac.
# The key tells apt "trust packages signed by Microsoft".
# The repo tells apt "look here for msodbcsql18".
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list

# Install ODBC Driver 18 for SQL Server.
# ACCEPT_EULA=Y is required — the driver has a Microsoft license agreement.
# unixodbc-dev provides the ODBC headers pyodbc needs to compile against.
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y \
    msodbcsql18 \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
# All subsequent COPY and RUN commands operate relative to this path.
WORKDIR /app

# Copy dependency files first — before copying any app code.
# Docker caches each layer. If pyproject.toml and poetry.lock haven't changed,
# Docker reuses the cached dep-install layer on the next build, even if code changed.
# This makes rebuilds much faster during development.
COPY pyproject.toml poetry.lock ./

# Install Poetry, then install only production dependencies directly into the
# system Python (not a virtualenv). POETRY_VIRTUALENVS_CREATE=false tells Poetry
# to skip creating a virtualenv and install straight into the active Python.
# --only main excludes dev dependencies (pytest, ruff) from the image.
# --no-root skips installing the project package itself (we COPY the code manually below).
RUN pip install --no-cache-dir poetry \
    && POETRY_VIRTUALENVS_CREATE=false poetry install --only main --no-root \
    && pip uninstall -y poetry

# Copy the app package into the container.
# This is done after dep install so that code changes don't invalidate the dep cache.
COPY app/ ./app/

# Copy trips.json — contains the route and trip dates to track.
# This file is gitignored (private), so you must create it from trips.example.json
# before building the image. The image is stored in a private ACR registry.
COPY trips.json ./

# The command Azure runs when the container starts.
# Runs the job once and exits — no web server, no long-running process.
CMD ["python", "-m", "app.main"]
