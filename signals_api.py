"""
Signals API - Signal generation endpoints
Place this file in project root alongside api.py

Add to your FastAPI app (api.py):
    from signals_api import router as signals_router
    app.include_router(signals_router)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["Signals"])

# ===== IN-MEMORY SIGNAL STORAGE (MVP) =====
# Will be replaced with database in Phase 2
_signals_storage: Dict[int, Any] = {}  # id -> TradingSignal
_signal_id_counter = 0


def store_signals(signals: List) -> None:
    """Store signals in memory with auto-incrementing IDs"""
    global _signal_id_counter, _signals_storage
    
    # Clear old signals (MVP: no persistence)
    _signals_storage.clear()
    
    for signal in signals:
        _signal_id_counter += 1
        signal_dict = signal.to_dict() if hasattr(signal, 'to_dict') else signal.__dict__
        signal_dict['id'] = _signal_id_counter
        _signals_storage[_signal_id_counter] = signal_dict


def get_all_signals() -> List[Dict]:
    """Get all stored signals"""
    return list(_signals_storage.values())


def get_signal_by_id(signal_id: int) -> Optional[Dict]:
    """Get single signal by ID"""
    return _signals_storage.get(signal_id)


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
        
        if result:
            signals = result if isinstance(result, list) else result.get('signals', [])
            
            # Store signals in memory
            store_signals(signals)
            
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


# ===== GET ENDPOINTS =====

@router.get("")
async def get_signals(
    status: str = "active",
    limit: int = 50,
    ticker_symbol: Optional[str] = None
):
    """
    Get all stored signals
    
    Query params:
    - status: active/expired/archived (default: active)
    - limit: max results (default: 50)
    - ticker_symbol: filter by ticker (optional)
    """
    try:
        signals = get_all_signals()
        
        # Filter by ticker if provided
        if ticker_symbol:
            signals = [s for s in signals if s.get('ticker_symbol') == ticker_symbol]
        
        # Limit results
        signals = signals[:limit]
        
        return {
            "signals": signals,
            "total": len(signals)
        }
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get signals: {str(e)}"
        )


@router.get("/{signal_id}")
async def get_signal_by_id_endpoint(signal_id: int):
    """
    Get single signal by ID
    
    Path param:
    - signal_id: Signal ID (auto-generated)
    
    Returns full signal object with components breakdown
    """
    try:
        signal = get_signal_by_id(signal_id)
        
        if not signal:
            raise HTTPException(
                status_code=404,
                detail=f"Signal with ID {signal_id} not found"
            )
        
        return signal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal {signal_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get signal: {str(e)}"
        )


# Export router
__all__ = ['router']
