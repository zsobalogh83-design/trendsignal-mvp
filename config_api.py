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

class TechnicalWeightsUpdate(BaseModel):
    """Model for updating technical component weights"""
    tech_sma20_bullish: Optional[int] = Field(None, ge=0, le=100)
    tech_sma20_bearish: Optional[int] = Field(None, ge=0, le=100)
    tech_sma50_bullish: Optional[int] = Field(None, ge=0, le=100)
    tech_sma50_bearish: Optional[int] = Field(None, ge=0, le=100)
    tech_golden_cross: Optional[int] = Field(None, ge=0, le=100)
    tech_death_cross: Optional[int] = Field(None, ge=0, le=100)
    tech_rsi_neutral: Optional[int] = Field(None, ge=0, le=100)
    tech_rsi_bullish: Optional[int] = Field(None, ge=0, le=100)
    tech_rsi_weak_bullish: Optional[int] = Field(None, ge=0, le=100)
    tech_rsi_overbought: Optional[int] = Field(None, ge=0, le=100)
    tech_rsi_oversold: Optional[int] = Field(None, ge=0, le=100)

class TechnicalWeightsResponse(BaseModel):
    """Response model for technical component weights"""
    tech_sma20_bullish: int
    tech_sma20_bearish: int
    tech_sma50_bullish: int
    tech_sma50_bearish: int
    tech_golden_cross: int
    tech_death_cross: int
    tech_rsi_neutral: int
    tech_rsi_bullish: int
    tech_rsi_weak_bullish: int
    tech_rsi_overbought: int
    tech_rsi_oversold: int

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


# ===== TECHNICAL COMPONENT WEIGHTS ENDPOINTS =====

@router.get("/technical-weights", response_model=TechnicalWeightsResponse)
async def get_technical_weights():
    """Get current technical component weights"""
    try:
        from src.config import get_config
        config = get_config()
        
        return TechnicalWeightsResponse(
            tech_sma20_bullish=config.tech_sma20_bullish,
            tech_sma20_bearish=config.tech_sma20_bearish,
            tech_sma50_bullish=config.tech_sma50_bullish,
            tech_sma50_bearish=config.tech_sma50_bearish,
            tech_golden_cross=config.tech_golden_cross,
            tech_death_cross=config.tech_death_cross,
            tech_rsi_neutral=config.tech_rsi_neutral,
            tech_rsi_bullish=config.tech_rsi_bullish,
            tech_rsi_weak_bullish=config.tech_rsi_weak_bullish,
            tech_rsi_overbought=config.tech_rsi_overbought,
            tech_rsi_oversold=config.tech_rsi_oversold
        )
    except Exception as e:
        logger.error(f"Error getting technical weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/technical-weights", response_model=TechnicalWeightsResponse)
async def update_technical_weights(updates: TechnicalWeightsUpdate):
    """Update technical component weights"""
    try:
        from src.config import get_config, update_config_values
        
        config = get_config()
        config_updates = {}
        
        if updates.tech_sma20_bullish is not None:
            config_updates["TECH_SMA20_BULLISH"] = updates.tech_sma20_bullish
        if updates.tech_sma20_bearish is not None:
            config_updates["TECH_SMA20_BEARISH"] = updates.tech_sma20_bearish
        if updates.tech_sma50_bullish is not None:
            config_updates["TECH_SMA50_BULLISH"] = updates.tech_sma50_bullish
        if updates.tech_sma50_bearish is not None:
            config_updates["TECH_SMA50_BEARISH"] = updates.tech_sma50_bearish
        if updates.tech_golden_cross is not None:
            config_updates["TECH_GOLDEN_CROSS"] = updates.tech_golden_cross
        if updates.tech_death_cross is not None:
            config_updates["TECH_DEATH_CROSS"] = updates.tech_death_cross
        if updates.tech_rsi_neutral is not None:
            config_updates["TECH_RSI_NEUTRAL"] = updates.tech_rsi_neutral
        if updates.tech_rsi_bullish is not None:
            config_updates["TECH_RSI_BULLISH"] = updates.tech_rsi_bullish
        if updates.tech_rsi_weak_bullish is not None:
            config_updates["TECH_RSI_WEAK_BULLISH"] = updates.tech_rsi_weak_bullish
        if updates.tech_rsi_overbought is not None:
            config_updates["TECH_RSI_OVERBOUGHT"] = updates.tech_rsi_overbought
        if updates.tech_rsi_oversold is not None:
            config_updates["TECH_RSI_OVERSOLD"] = updates.tech_rsi_oversold
        
        if not config_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        update_config_values(config, config_updates)
        
        logger.info(f"Technical weights updated: {config_updates}")
        
        return await get_technical_weights()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating technical weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

