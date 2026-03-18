FROM python:3.12-slim

WORKDIR /app

# psycopg2 requires libpq headers and a C compiler to build from source.
# These are removed after install to keep the image lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the dashboard package is needed at runtime.
# Alembic migrations run from the developer's machine, not from this image.
COPY dashboard/ ./dashboard/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["./entrypoint.sh"]
