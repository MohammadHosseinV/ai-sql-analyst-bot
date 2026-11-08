# =============================================================================
# Autonomous Data Analyst - Database Seeder Dockerfile
# Base: Python 3.11 Slim with UTF-8 and PostgreSQL Client Libraries
# =============================================================================

FROM python:3.11-slim

# Enforce clean Python runtime environment and UTF-8 encoding
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# Install runtime library dependencies for PostgreSQL client and clean cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seeder script
COPY seed_data.py .

# Execute database seeding
CMD ["python", "seed_data.py"]
