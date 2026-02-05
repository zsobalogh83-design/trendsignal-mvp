"""
Tickers API - Ticker CRUD endpoints with keyword management
Separate router to keep api.py clean

Version: 1.0
Date: 2026-02-04
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import logging

# Database imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.database import get_db
from src.models import Ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tickers", tags=["Tickers"])


# ==========================================
# PYDANTIC MODELS
# ==========================================

class TickerBase(BaseModel):
    """Base ticker data"""
    symbol: str = Field(..., max_length=10)
    name: Optional[str] = Field(None, max_length=100)
    market: Optional[str] = Field(None, max_length=20)
    industry: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=3)
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    is_active: bool = True
    primary_language: str = Field(default="en", max_length=5)


class TickerCreate(TickerBase):
    """Ticker creation payload"""
    relevance_keywords: Optional[List[str]] = []
    sentiment_keywords_positive: Optional[List[str]] = []
    sentiment_keywords_negative: Optional[List[str]] = []
    news_sources_preferred: Optional[List[str]] = []
    news_sources_blocked: Optional[List[str]] = []


class TickerUpdate(BaseModel):
    """Ticker update payload - all fields optional"""
    name: Optional[str] = None
    market: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    currency: Optional[str] = None
    priority: Optional[str] = None
    is_active: Optional[bool] = None
    primary_language: Optional[str] = None
    relevance_keywords: Optional[List[str]] = None
    sentiment_keywords_positive: Optional[List[str]] = None
    sentiment_keywords_negative: Optional[List[str]] = None
    news_sources_preferred: Optional[List[str]] = None
    news_sources_blocked: Optional[List[str]] = None


class TickerResponse(BaseModel):
    """Ticker response with all fields"""
    id: int
    symbol: str
    name: Optional[str]
    market: Optional[str]
    industry: Optional[str]
    sector: Optional[str]
    currency: Optional[str]
    priority: str
    is_active: bool
    primary_language: str
    relevance_keywords: List[str]
    sentiment_keywords_positive: List[str]
    sentiment_keywords_negative: List[str]
    news_sources_preferred: List[str]
    news_sources_blocked: List[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def ticker_to_response(ticker: Ticker) -> dict:
    """Convert Ticker model to response dict"""
    return {
        "id": ticker.id,
        "symbol": ticker.symbol,
        "name": ticker.name,
        "market": ticker.market,
        "industry": ticker.industry,
        "sector": ticker.sector,
        "currency": ticker.currency,
        "priority": ticker.priority or "medium",
        "is_active": ticker.is_active,
        "primary_language": ticker.primary_language or "en",
        "relevance_keywords": json.loads(ticker.relevance_keywords) if ticker.relevance_keywords else [],
        "sentiment_keywords_positive": json.loads(ticker.sentiment_keywords_positive) if ticker.sentiment_keywords_positive else [],
        "sentiment_keywords_negative": json.loads(ticker.sentiment_keywords_negative) if ticker.sentiment_keywords_negative else [],
        "news_sources_preferred": json.loads(ticker.news_sources_preferred) if ticker.news_sources_preferred else [],
        "news_sources_blocked": json.loads(ticker.news_sources_blocked) if ticker.news_sources_blocked else [],
        "created_at": ticker.created_at.isoformat() if ticker.created_at else None,
        "updated_at": ticker.updated_at.isoformat() if ticker.updated_at else None
    }


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("", response_model=List[TickerResponse])
async def list_tickers(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Get all tickers with full details
    
    Query params:
    - is_active: Filter by active status (optional)
    """
    try:
        query = db.query(Ticker)
        
        if is_active is not None:
            query = query.filter(Ticker.is_active == is_active)
        
        tickers = query.order_by(Ticker.priority.desc(), Ticker.symbol.asc()).all()
        
        return [ticker_to_response(ticker) for ticker in tickers]
        
    except Exception as e:
        logger.error(f"Error listing tickers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker_id}", response_model=TickerResponse)
async def get_ticker(
    ticker_id: int,
    db: Session = Depends(get_db)
):
    """Get single ticker by ID with full details"""
    try:
        ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker_id} not found")
        
        return ticker_to_response(ticker)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker {ticker_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=TickerResponse, status_code=201)
async def create_ticker(
    ticker_data: TickerCreate,
    db: Session = Depends(get_db)
):
    """Create new ticker"""
    try:
        # Check if ticker already exists
        existing = db.query(Ticker).filter(Ticker.symbol == ticker_data.symbol).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Ticker {ticker_data.symbol} already exists")
        
        # Create new ticker
        new_ticker = Ticker(
            symbol=ticker_data.symbol,
            name=ticker_data.name,
            market=ticker_data.market,
            industry=ticker_data.industry,
            sector=ticker_data.sector,
            currency=ticker_data.currency,
            priority=ticker_data.priority,
            is_active=ticker_data.is_active,
            primary_language=ticker_data.primary_language,
            relevance_keywords=json.dumps(ticker_data.relevance_keywords) if ticker_data.relevance_keywords else None,
            sentiment_keywords_positive=json.dumps(ticker_data.sentiment_keywords_positive) if ticker_data.sentiment_keywords_positive else None,
            sentiment_keywords_negative=json.dumps(ticker_data.sentiment_keywords_negative) if ticker_data.sentiment_keywords_negative else None,
            news_sources_preferred=json.dumps(ticker_data.news_sources_preferred) if ticker_data.news_sources_preferred else None,
            news_sources_blocked=json.dumps(ticker_data.news_sources_blocked) if ticker_data.news_sources_blocked else None
        )
        
        db.add(new_ticker)
        db.commit()
        db.refresh(new_ticker)
        
        logger.info(f"✅ Created ticker: {new_ticker.symbol}")
        
        return ticker_to_response(new_ticker)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating ticker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{ticker_id}", response_model=TickerResponse)
async def update_ticker(
    ticker_id: int,
    ticker_data: TickerUpdate,
    db: Session = Depends(get_db)
):
    """Update existing ticker"""
    try:
        ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker_id} not found")
        
        # Update fields if provided
        update_data = ticker_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field in ['relevance_keywords', 'sentiment_keywords_positive', 
                        'sentiment_keywords_negative', 'news_sources_preferred', 
                        'news_sources_blocked']:
                # Convert lists to JSON strings
                setattr(ticker, field, json.dumps(value) if value is not None else None)
            else:
                # Set scalar values directly
                setattr(ticker, field, value)
        
        db.commit()
        db.refresh(ticker)
        
        logger.info(f"✅ Updated ticker: {ticker.symbol}")
        
        return ticker_to_response(ticker)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating ticker {ticker_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ticker_id}", status_code=204)
async def delete_ticker(
    ticker_id: int,
    db: Session = Depends(get_db)
):
    """
    Soft delete ticker (sets is_active = False)
    Does NOT delete from database to preserve historical data
    """
    try:
        ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker_id} not found")
        
        # Soft delete - just deactivate
        ticker.is_active = False
        db.commit()
        
        logger.info(f"🗑️ Deactivated ticker: {ticker.symbol}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting ticker {ticker_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ticker_id}/toggle", response_model=TickerResponse)
async def toggle_ticker_active(
    ticker_id: int,
    db: Session = Depends(get_db)
):
    """Quick toggle ticker active status"""
    try:
        ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker_id} not found")
        
        # Toggle
        ticker.is_active = not ticker.is_active
        db.commit()
        db.refresh(ticker)
        
        status = "activated" if ticker.is_active else "deactivated"
        logger.info(f"🔄 {status.capitalize()} ticker: {ticker.symbol}")
        
        return ticker_to_response(ticker)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling ticker {ticker_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":
    print("✅ Tickers API Router")
    print("📊 Endpoints:")
    print("  GET    /api/v1/tickers       - List all tickers")
    print("  GET    /api/v1/tickers/{id}  - Get ticker details")
    print("  POST   /api/v1/tickers       - Create ticker")
    print("  PUT    /api/v1/tickers/{id}  - Update ticker")
    print("  DELETE /api/v1/tickers/{id}  - Soft delete ticker")
    print("  PATCH  /api/v1/tickers/{id}/toggle - Toggle active status")
