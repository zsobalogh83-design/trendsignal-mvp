"""
Configuration API - Standalone module
Place this file in project root alongside main.py or api.py

Add to your FastAPI app:
    from config_api import router as config_router
    app.include_router(config_router)
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])

# ===== REQUEST/RESPONSE MODELS =====

class SignalConfigUpdate(BaseModel):
    """Model for updating signal configuration"""
    sentiment_weight: Optional[float] = Field(None, ge=0, le=1)
    technical_weight: Optional[float] = Field(None, ge=0, le=1)
    risk_weight: Optional[float] = Field(None, ge=0, le=1)
    
    strong_buy_score: Optional[int] = Field(None, ge=0, le=100)
    strong_buy_confidence: Optional[float] = Field(None, ge=0, le=1)
    moderate_buy_score: Optional[int] = Field(None, ge=0, le=100)
    moderate_buy_confidence: Optional[float] = Field(None, ge=0, le=1)
    
    strong_sell_score: Optional[int] = Field(None, ge=-100, le=0)
    strong_sell_confidence: Optional[float] = Field(None, ge=0, le=1)
    moderate_sell_score: Optional[int] = Field(None, ge=-100, le=0)
    moderate_sell_confidence: Optional[float] = Field(None, ge=0, le=1)

class SignalConfigResponse(BaseModel):
    """Response model for signal configuration"""
    sentiment_weight: float
    technical_weight: float
    risk_weight: float
    strong_buy_score: int
    strong_buy_confidence: float
    moderate_buy_score: int
    moderate_buy_confidence: float
    strong_sell_score: int
    strong_sell_confidence: float
    moderate_sell_score: int
    moderate_sell_confidence: float

class DecayWeightsUpdate(BaseModel):
    """Model for updating decay weights (as percentages 0-100)"""
    fresh_0_2h: Optional[int] = Field(None, ge=0, le=100)
    strong_2_6h: Optional[int] = Field(None, ge=0, le=100)
    intraday_6_12h: Optional[int] = Field(None, ge=0, le=100)
    overnight_12_24h: Optional[int] = Field(None, ge=0, le=100)

class DecayWeightsResponse(BaseModel):
    """Response model for decay weights (as percentages)"""
    fresh_0_2h: int
    strong_2_6h: int
    intraday_6_12h: int
    overnight_12_24h: int

# ===== ENDPOINTS =====

@router.get("/signal", response_model=SignalConfigResponse)
async def get_signal_config():
    """Get current signal configuration"""
    try:
        from src.config import get_config
        config = get_config()
        
        return SignalConfigResponse(
            sentiment_weight=config.SENTIMENT_WEIGHT,
            technical_weight=config.TECHNICAL_WEIGHT,
            risk_weight=config.RISK_WEIGHT,
            strong_buy_score=config.STRONG_BUY_SCORE,
            strong_buy_confidence=config.STRONG_BUY_CONFIDENCE,
            moderate_buy_score=config.MODERATE_BUY_SCORE,
            moderate_buy_confidence=config.MODERATE_BUY_CONFIDENCE,
            strong_sell_score=config.STRONG_SELL_SCORE,
            strong_sell_confidence=config.STRONG_SELL_CONFIDENCE,
            moderate_sell_score=config.MODERATE_SELL_SCORE,
            moderate_sell_confidence=config.MODERATE_SELL_CONFIDENCE
        )
    except Exception as e:
        logger.error(f"Error getting signal config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/signal", response_model=SignalConfigResponse)
async def update_signal_config(config_update: SignalConfigUpdate):
    """Update signal configuration"""
    try:
        from src.config import get_config, update_config_values
        
        config = get_config()
        updates = {}
        
        # Check if all weights are provided
        weights_provided = all([
            config_update.sentiment_weight is not None,
            config_update.technical_weight is not None,
            config_update.risk_weight is not None
        ])
        
        if weights_provided:
            # Validate sum = 1.0
            total = config_update.sentiment_weight + config_update.technical_weight + config_update.risk_weight
            if abs(total - 1.0) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Weights must sum to 1.0, got {total:.3f}"
                )
            
            updates["SENTIMENT_WEIGHT"] = config_update.sentiment_weight
            updates["TECHNICAL_WEIGHT"] = config_update.technical_weight
            updates["RISK_WEIGHT"] = config_update.risk_weight
        
        # Add threshold updates
        if config_update.strong_buy_score is not None:
            updates["STRONG_BUY_SCORE"] = config_update.strong_buy_score
        if config_update.strong_buy_confidence is not None:
            updates["STRONG_BUY_CONFIDENCE"] = config_update.strong_buy_confidence
        if config_update.moderate_buy_score is not None:
            updates["MODERATE_BUY_SCORE"] = config_update.moderate_buy_score
        if config_update.moderate_buy_confidence is not None:
            updates["MODERATE_BUY_CONFIDENCE"] = config_update.moderate_buy_confidence
        if config_update.strong_sell_score is not None:
            updates["STRONG_SELL_SCORE"] = config_update.strong_sell_score
        if config_update.strong_sell_confidence is not None:
            updates["STRONG_SELL_CONFIDENCE"] = config_update.strong_sell_confidence
        if config_update.moderate_sell_score is not None:
            updates["MODERATE_SELL_SCORE"] = config_update.moderate_sell_score
        if config_update.moderate_sell_confidence is not None:
            updates["MODERATE_SELL_CONFIDENCE"] = config_update.moderate_sell_confidence
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        # Update config
        update_config_values(config, updates)
        
        logger.info(f"Config updated: {updates}")
        
        # Return updated config
        return await get_signal_config()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/signal/reset")
async def reset_signal_config():
    """Reset configuration to defaults"""
    try:
        from src.config import get_config, update_config_values
        
        config = get_config()
        
        # Default values
        updates = {
            "SENTIMENT_WEIGHT": 0.7,
            "TECHNICAL_WEIGHT": 0.2,
            "RISK_WEIGHT": 0.1,
            "STRONG_BUY_SCORE": 65,
            "STRONG_BUY_CONFIDENCE": 0.75,
            "MODERATE_BUY_SCORE": 50,
            "MODERATE_BUY_CONFIDENCE": 0.65,
            "STRONG_SELL_SCORE": -65,
            "STRONG_SELL_CONFIDENCE": 0.75,
            "MODERATE_SELL_SCORE": -50,
            "MODERATE_SELL_CONFIDENCE": 0.65,
        }
        
        update_config_values(config, updates)
        
        logger.info("Config reset to defaults")
        
        return {
            "message": "Configuration reset to defaults",
            "config": await get_signal_config()
        }
        
    except Exception as e:
        logger.error(f"Error resetting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/reload")
async def reload_configuration():
    """Reload configuration from file"""
    try:
        from src.config import reload_config
        
        reload_config()
        
        logger.info("Config reloaded")
        
        return {
            "message": "Configuration reloaded",
            "config": await get_signal_config()
        }
        
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== DECAY WEIGHTS ENDPOINTS =====

@router.get("/decay", response_model=DecayWeightsResponse)
async def get_decay_weights():
    """Get current sentiment decay weights"""
    try:
        from src.config import get_config
        config = get_config()
        
        # Convert from decimal (0-1) to percentage (0-100)
        return DecayWeightsResponse(
            fresh_0_2h=int(config.decay_weights.get('0-2h', 1.0) * 100),
            strong_2_6h=int(config.decay_weights.get('2-6h', 0.85) * 100),
            intraday_6_12h=int(config.decay_weights.get('6-12h', 0.60) * 100),
            overnight_12_24h=int(config.decay_weights.get('12-24h', 0.35) * 100)
        )
    except Exception as e:
        logger.error(f"Error getting decay weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/decay", response_model=DecayWeightsResponse)
async def update_decay_weights(updates: DecayWeightsUpdate):
    """Update sentiment decay weights"""
    try:
        from src.config import get_config, save_config_to_file
        
        config = get_config()
        
        # Update decay_weights dict (convert percentage to decimal)
        if updates.fresh_0_2h is not None:
            config.decay_weights['0-2h'] = updates.fresh_0_2h / 100
        if updates.strong_2_6h is not None:
            config.decay_weights['2-6h'] = updates.strong_2_6h / 100
        if updates.intraday_6_12h is not None:
            config.decay_weights['6-12h'] = updates.intraday_6_12h / 100
        if updates.overnight_12_24h is not None:
            config.decay_weights['12-24h'] = updates.overnight_12_24h / 100
        
        # Save to file
        save_config_to_file(config)
        
        logger.info(f"Decay weights updated: {config.decay_weights}")
        
        return await get_decay_weights()
        
    except Exception as e:
        logger.error(f"Error updating decay weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

