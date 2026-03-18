#!/bin/bash
set -e

# In ECS, DATABASE_URL is assembled here from individually injected environment
# variables. DB_USER and DB_PASSWORD arrive via Secrets Manager; DB_HOST,
# DB_PORT, and DB_NAME are plain task environment variables.
#
# Locally, DATABASE_URL is already present (set by python-dotenv from .env),
# so this block is skipped and nothing changes.
if [ -z "${DATABASE_URL}" ]; then
    export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT:-5432}/${DB_NAME:-pdga_data}"
fi

exec streamlit run dashboard/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
