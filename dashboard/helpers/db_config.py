# helpers/db_config.py

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DG_READER_URL = os.getenv("DG_READER_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

engine = create_engine(DATABASE_URL)

# Read-only engine for Claude-generated queries (search feature).
# Falls back to None if DG_READER_URL is not set (e.g. local dev before dg_reader is created).
reader_engine = create_engine(DG_READER_URL) if DG_READER_URL else None