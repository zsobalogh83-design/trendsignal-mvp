"""
Database configuration and session management
SQLite setup for TrendSignal MVP
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os

# Database URL - SQLite in PROJECT ROOT (parent directory of src/)
# This ensures we use the main trendsignal.db, not src/trendsignal.db
BASE_DIR = Path(__file__).resolve().parent.parent  # Go up from src/ to project root
DATABASE_PATH = BASE_DIR / "trendsignal.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

print(f"📁 Database path: {DATABASE_PATH}")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

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
    # Import models to register them with Base
    import models  # This registers all models
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
