"""
Signals API - Signal generation endpoints
Place this file in project root alongside api.py

Add to your FastAPI app (api.py):
    from signals_api import router as signals_router
    app.include_router(signals_router)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["Signals"])


# ===== REQUEST/RESPONSE MODELS =====

class GenerateSignalsRequest(BaseModel):
    """Request model for signal generation"""
    tickers: Optional[List[str]] = None  # If None, generate for all active tickers
    force_refresh: bool = False  # Force news collection before generation

class GenerateSignalsResponse(BaseModel):
    """Response model for signal generation"""
    message: str
    signals_generated: int
    tickers_processed: List[str]


# ===== ENDPOINTS =====

@router.post("/generate", response_model=GenerateSignalsResponse)
async def generate_all_signals(request: GenerateSignalsRequest = None):
    """
    Generate trading signals for all active tickers
    
    This endpoint:
    1. Collects latest news (if force_refresh=True)
    2. Analyzes sentiment with decay model
    3. Calculates technical indicators
    4. Generates BUY/SELL/HOLD signals
    5. Returns count of generated signals
    """
    try:
        from main import run_batch_analysis
        
        logger.info("Signal generation triggered via API")
        
        # Default tickers if none provided
        default_tickers = [
            {'symbol': 'AAPL', 'name': 'Apple Inc'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc'}
        ]
        
        tickers_to_process = default_tickers
        if request and request.tickers:
            # Convert list of symbols to list of dicts
            tickers_to_process = [{'symbol': t, 'name': t} for t in request.tickers]
        
        # Run analysis with tickers parameter
        result = run_batch_analysis(tickers_to_process)
        
        if result and 'signals' in result:
            signals = result['signals']
            
            return GenerateSignalsResponse(
                message=f"Successfully generated {len(signals)} signals",
                signals_generated=len(signals),
                tickers_processed=[s.ticker_symbol for s in signals]
            )
        else:
            return GenerateSignalsResponse(
                message="Signal generation completed but no signals returned",
                signals_generated=0,
                tickers_processed=[]
            )
        
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signals: {str(e)}"
        )


@router.post("/generate/{ticker_symbol}", response_model=GenerateSignalsResponse)
async def generate_single_signal(ticker_symbol: str):
    """
    Generate trading signal for a single ticker
    
    Args:
        ticker_symbol: Stock ticker (e.g., AAPL, MSFT)
    """
    try:
        from main import run_analysis
        
        logger.info(f"Signal generation triggered for {ticker_symbol}")
        
        # Run analysis for single ticker
        signal = run_analysis(ticker_symbol)
        
        if signal:
            return GenerateSignalsResponse(
                message=f"Successfully generated signal for {ticker_symbol}",
                signals_generated=1,
                tickers_processed=[ticker_symbol]
            )
        else:
            return GenerateSignalsResponse(
                message=f"No signal generated for {ticker_symbol}",
                signals_generated=0,
                tickers_processed=[]
            )
        
    except Exception as e:
        logger.error(f"Error generating signal for {ticker_symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signal: {str(e)}"
        )


@router.post("/refresh")
async def refresh_signals(background_tasks: BackgroundTasks):
    """
    Refresh all signals (collect news + generate signals)
    Runs in background to avoid timeout
    """
    try:
        from main import run_batch_analysis
        
        logger.info("Signal refresh triggered (with news collection)")
        
        # Add task to background
        background_tasks.add_task(run_batch_analysis)
        
        return {
            "message": "Signal refresh started in background",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh signals: {str(e)}"
        )


# Export router
__all__ = ['router']
