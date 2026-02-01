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

# ===== NEW: INDICATOR PARAMETERS MODELS =====

class IndicatorParametersUpdate(BaseModel):
    """Model for updating technical indicator parameters"""
    # RSI
    rsi_period: Optional[int] = Field(None, ge=5, le=50)
    rsi_timeframe: Optional[str] = None
    rsi_lookback: Optional[str] = None
    # SMA Short
    sma_short_period: Optional[int] = Field(None, ge=5, le=100)
    sma_short_timeframe: Optional[str] = None
    sma_short_lookback: Optional[str] = None
    # SMA Medium
    sma_medium_period: Optional[int] = Field(None, ge=20, le=200)
    sma_medium_timeframe: Optional[str] = None
    sma_medium_lookback: Optional[str] = None
    # SMA Long
    sma_long_period: Optional[int] = Field(None, ge=100, le=300)
    sma_long_timeframe: Optional[str] = None
    sma_long_lookback: Optional[str] = None
    # MACD
    macd_fast: Optional[int] = Field(None, ge=5, le=50)
    macd_slow: Optional[int] = Field(None, ge=10, le=100)
    macd_signal: Optional[int] = Field(None, ge=5, le=50)
    macd_timeframe: Optional[str] = None
    macd_lookback: Optional[str] = None
    # Bollinger Bands
    bb_period: Optional[int] = Field(None, ge=10, le=50)
    bb_std_dev: Optional[float] = Field(None, ge=1.0, le=3.0)
    bb_timeframe: Optional[str] = None
    bb_lookback: Optional[str] = None
    # ATR
    atr_period: Optional[int] = Field(None, ge=5, le=50)
    atr_timeframe: Optional[str] = None
    atr_lookback: Optional[str] = None
    # Stochastic
    stoch_period: Optional[int] = Field(None, ge=5, le=50)
    stoch_timeframe: Optional[str] = None
    stoch_lookback: Optional[str] = None
    # ADX
    adx_period: Optional[int] = Field(None, ge=5, le=50)
    adx_timeframe: Optional[str] = None
    adx_lookback: Optional[str] = None

class IndicatorParametersResponse(BaseModel):
    """Response model for technical indicator parameters"""
    # RSI
    rsi_period: int
    rsi_timeframe: str
    rsi_lookback: str
    # SMA Short
    sma_short_period: int
    sma_short_timeframe: str
    sma_short_lookback: str
    # SMA Medium
    sma_medium_period: int
    sma_medium_timeframe: str
    sma_medium_lookback: str
    # SMA Long
    sma_long_period: int
    sma_long_timeframe: str
    sma_long_lookback: str
    # MACD
    macd_fast: int
    macd_slow: int
    macd_signal: int
    macd_timeframe: str
    macd_lookback: str
    # Bollinger Bands
    bb_period: int
    bb_std_dev: float
    bb_timeframe: str
    bb_lookback: str
    # ATR
    atr_period: int
    atr_timeframe: str
    atr_lookback: str
    # Stochastic
    stoch_period: int
    stoch_timeframe: str
    stoch_lookback: str
    # ADX
    adx_period: int
    adx_timeframe: str
    adx_lookback: str

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


# ===== NEW: INDICATOR PARAMETERS ENDPOINTS =====

@router.get("/indicator-parameters", response_model=IndicatorParametersResponse)
async def get_indicator_parameters():
    """Get current technical indicator parameters"""
    try:
        from src.config import get_config
        config = get_config()
        
        return IndicatorParametersResponse(
            # RSI
            rsi_period=config.rsi_period,
            rsi_timeframe=config.rsi_timeframe,
            rsi_lookback=config.rsi_lookback,
            # SMA Short
            sma_short_period=config.sma_short_period,
            sma_short_timeframe=config.sma_short_timeframe,
            sma_short_lookback=config.sma_short_lookback,
            # SMA Medium
            sma_medium_period=config.sma_medium_period,
            sma_medium_timeframe=config.sma_medium_timeframe,
            sma_medium_lookback=config.sma_medium_lookback,
            # SMA Long
            sma_long_period=config.sma_long_period,
            sma_long_timeframe=config.sma_long_timeframe,
            sma_long_lookback=config.sma_long_lookback,
            # MACD
            macd_fast=config.macd_fast,
            macd_slow=config.macd_slow,
            macd_signal=config.macd_signal,
            macd_timeframe=config.macd_timeframe,
            macd_lookback=config.macd_lookback,
            # Bollinger Bands
            bb_period=config.bb_period,
            bb_std_dev=config.bb_std_dev,
            bb_timeframe=config.bb_timeframe,
            bb_lookback=config.bb_lookback,
            # ATR
            atr_period=config.atr_period,
            atr_timeframe=config.atr_timeframe,
            atr_lookback=config.atr_lookback,
            # Stochastic
            stoch_period=config.stoch_period,
            stoch_timeframe=config.stoch_timeframe,
            stoch_lookback=config.stoch_lookback,
            # ADX
            adx_period=config.adx_period,
            adx_timeframe=config.adx_timeframe,
            adx_lookback=config.adx_lookback,
        )
    except Exception as e:
        logger.error(f"Error getting indicator parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/indicator-parameters", response_model=IndicatorParametersResponse)
async def update_indicator_parameters(updates: IndicatorParametersUpdate):
    """Update technical indicator parameters"""
    try:
        from src.config import get_config, update_config_values
        
        config = get_config()
        config_updates = {}
        
        # RSI
        if updates.rsi_period is not None:
            config_updates["RSI_PERIOD"] = updates.rsi_period
        if updates.rsi_timeframe is not None:
            config_updates["RSI_TIMEFRAME"] = updates.rsi_timeframe
        if updates.rsi_lookback is not None:
            config_updates["RSI_LOOKBACK"] = updates.rsi_lookback
        
        # SMA Short
        if updates.sma_short_period is not None:
            config_updates["SMA_SHORT_PERIOD"] = updates.sma_short_period
        if updates.sma_short_timeframe is not None:
            config_updates["SMA_SHORT_TIMEFRAME"] = updates.sma_short_timeframe
        if updates.sma_short_lookback is not None:
            config_updates["SMA_SHORT_LOOKBACK"] = updates.sma_short_lookback
        
        # SMA Medium
        if updates.sma_medium_period is not None:
            config_updates["SMA_MEDIUM_PERIOD"] = updates.sma_medium_period
        if updates.sma_medium_timeframe is not None:
            config_updates["SMA_MEDIUM_TIMEFRAME"] = updates.sma_medium_timeframe
        if updates.sma_medium_lookback is not None:
            config_updates["SMA_MEDIUM_LOOKBACK"] = updates.sma_medium_lookback
        
        # SMA Long
        if updates.sma_long_period is not None:
            config_updates["SMA_LONG_PERIOD"] = updates.sma_long_period
        if updates.sma_long_timeframe is not None:
            config_updates["SMA_LONG_TIMEFRAME"] = updates.sma_long_timeframe
        if updates.sma_long_lookback is not None:
            config_updates["SMA_LONG_LOOKBACK"] = updates.sma_long_lookback
        
        # MACD
        if updates.macd_fast is not None:
            config_updates["MACD_FAST"] = updates.macd_fast
        if updates.macd_slow is not None:
            config_updates["MACD_SLOW"] = updates.macd_slow
        if updates.macd_signal is not None:
            config_updates["MACD_SIGNAL"] = updates.macd_signal
        if updates.macd_timeframe is not None:
            config_updates["MACD_TIMEFRAME"] = updates.macd_timeframe
        if updates.macd_lookback is not None:
            config_updates["MACD_LOOKBACK"] = updates.macd_lookback
        
        # Bollinger Bands
        if updates.bb_period is not None:
            config_updates["BB_PERIOD"] = updates.bb_period
        if updates.bb_std_dev is not None:
            config_updates["BB_STD_DEV"] = updates.bb_std_dev
        if updates.bb_timeframe is not None:
            config_updates["BB_TIMEFRAME"] = updates.bb_timeframe
        if updates.bb_lookback is not None:
            config_updates["BB_LOOKBACK"] = updates.bb_lookback
        
        # ATR
        if updates.atr_period is not None:
            config_updates["ATR_PERIOD"] = updates.atr_period
        if updates.atr_timeframe is not None:
            config_updates["ATR_TIMEFRAME"] = updates.atr_timeframe
        if updates.atr_lookback is not None:
            config_updates["ATR_LOOKBACK"] = updates.atr_lookback
        
        # Stochastic
        if updates.stoch_period is not None:
            config_updates["STOCH_PERIOD"] = updates.stoch_period
        if updates.stoch_timeframe is not None:
            config_updates["STOCH_TIMEFRAME"] = updates.stoch_timeframe
        if updates.stoch_lookback is not None:
            config_updates["STOCH_LOOKBACK"] = updates.stoch_lookback
        
        # ADX
        if updates.adx_period is not None:
            config_updates["ADX_PERIOD"] = updates.adx_period
        if updates.adx_timeframe is not None:
            config_updates["ADX_TIMEFRAME"] = updates.adx_timeframe
        if updates.adx_lookback is not None:
            config_updates["ADX_LOOKBACK"] = updates.adx_lookback
        
        if not config_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        update_config_values(config, config_updates)
        
        logger.info(f"Indicator parameters updated: {config_updates}")
        
        return await get_indicator_parameters()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating indicator parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
