"""
Database configuration and session management
SQLite setup for TrendSignal MVP
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL - SQLite in project root
DATABASE_URL = "sqlite:///./trendsignal.db"

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
