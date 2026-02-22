"""
Database configuration and session management
SQLite setup for TrendSignal MVP

VERSION: 1.1 - SQLite Lock Fix
DATE: 2026-02-03
CHANGES: Added timeout and WAL mode to prevent "database is locked" errors
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os

# Database URL - SQLite in PROJECT ROOT (parent directory of src/)
# This ensures we use the main trendsignal.db, not src/trendsignal.db
BASE_DIR = Path(__file__).resolve().parent.parent  # Go up from src/ to project root
DATABASE_PATH = BASE_DIR / "trendsignal.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

print(f"[DB] Database path: {DATABASE_PATH}")

# Create engine with LOCK PREVENTION settings
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Allow multi-threading
        "timeout": 30  # Wait up to 30 seconds for lock release (default: 5s)
    },
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for SQL debugging
)

# Enable WAL mode for better concurrency (SQLite 3.7.0+)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas on connection"""
    cursor = dbapi_conn.cursor()
    # WAL mode allows concurrent reads during writes
    cursor.execute("PRAGMA journal_mode=WAL")
    # Synchronous=NORMAL is faster and safe with WAL
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Increase cache size for better performance (default: 2000 pages)
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database (create all tables)
def init_db():
    """Create all tables in the database"""
    # Lazy import to avoid duplicate registry issues
    # Only import when actually creating tables
    try:
        import src.models  # This registers all models
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        # Tables might already exist, that's OK
        print(f"ℹ️ Database initialization: {e}")
        pass
