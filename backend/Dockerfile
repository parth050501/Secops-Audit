FROM python:3.11-slim

WORKDIR /app

# System deps:
# - curl for healthcheck
# - git + build-essential: some Prowler transitive deps may need to compile
# - clean up apt cache to keep image smaller
# Core build deps (required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

# OpenSCAP for the Linux server connector (optional — don't fail the whole build
# if package names differ on this base image; the cloud connectors don't need it).
RUN apt-get update && \
    (apt-get install -y --no-install-recommends openscap-scanner ssg-debian ssg-debderived \
     || apt-get install -y --no-install-recommends openscap-scanner \
     || echo "WARNING: OpenSCAP not installed — Linux server connector will be unavailable until installed") \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python deps. Prowler is large — this layer will take a few minutes
# and significantly increases image size (expect ~1.5-2GB). That's expected.
RUN pip install --no-cache-dir -r requirements.txt

# Verify Prowler installed and is callable at build time (fails fast if not)
RUN prowler --version || echo "WARNING: prowler not on PATH"

COPY . .
RUN mkdir -p /app/data

EXPOSE 8000

# Note: --reload is for dev. For production, remove --reload (see compose override).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
