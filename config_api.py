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

# ===== NEW: RISK PARAMETERS MODELS =====

class RiskParametersUpdate(BaseModel):
    """Model for updating risk management parameters"""
    # Risk Component Weights
    risk_volatility_weight: Optional[float] = Field(None, ge=0, le=1)
    risk_proximity_weight: Optional[float] = Field(None, ge=0, le=1)
    risk_trend_strength_weight: Optional[float] = Field(None, ge=0, le=1)
    # Stop-Loss / Take-Profit Multipliers
    stop_loss_sr_buffer: Optional[float] = Field(None, ge=0.1, le=2.0)
    stop_loss_atr_mult: Optional[float] = Field(None, ge=0.5, le=5.0)
    take_profit_atr_mult: Optional[float] = Field(None, ge=1.0, le=10.0)
    # S/R Distance Thresholds
    sr_support_max_distance_pct: Optional[float] = Field(None, ge=1.0, le=20.0)
    sr_resistance_max_distance_pct: Optional[float] = Field(None, ge=1.0, le=20.0)
    # S/R DBSCAN Parameters
    sr_dbscan_eps: Optional[float] = Field(None, ge=1.0, le=10.0)
    sr_dbscan_min_samples: Optional[int] = Field(None, ge=2, le=10)
    sr_dbscan_order: Optional[int] = Field(None, ge=3, le=14)
    sr_dbscan_lookback: Optional[int] = Field(None, ge=30, le=365)

class RiskParametersResponse(BaseModel):
    """Response model for risk management parameters"""
    # Risk Component Weights
    risk_volatility_weight: float
    risk_proximity_weight: float
    risk_trend_strength_weight: float
    # Stop-Loss / Take-Profit Multipliers
    stop_loss_sr_buffer: float
    stop_loss_atr_mult: float
    take_profit_atr_mult: float
    # S/R Distance Thresholds
    sr_support_max_distance_pct: float
    sr_resistance_max_distance_pct: float
    # S/R DBSCAN Parameters
    sr_dbscan_eps: float
    sr_dbscan_min_samples: int
    sr_dbscan_order: int
    sr_dbscan_lookback: int

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


# ===== NEW: RISK PARAMETERS ENDPOINTS =====

@router.get("/risk-parameters", response_model=RiskParametersResponse)
async def get_risk_parameters():
    """Get current risk management parameters"""
    try:
        from src.config import get_config
        config = get_config()
        
        return RiskParametersResponse(
            risk_volatility_weight=config.risk_volatility_weight,
            risk_proximity_weight=config.risk_proximity_weight,
            risk_trend_strength_weight=config.risk_trend_strength_weight,
            stop_loss_sr_buffer=config.stop_loss_sr_buffer,
            stop_loss_atr_mult=config.stop_loss_atr_mult,
            take_profit_atr_mult=config.take_profit_atr_mult,
            sr_support_max_distance_pct=config.sr_support_max_distance_pct,
            sr_resistance_max_distance_pct=config.sr_resistance_max_distance_pct,
            sr_dbscan_eps=config.sr_dbscan_eps,
            sr_dbscan_min_samples=config.sr_dbscan_min_samples,
            sr_dbscan_order=config.sr_dbscan_order,
            sr_dbscan_lookback=config.sr_dbscan_lookback,
        )
    except Exception as e:
        logger.error(f"Error getting risk parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/risk-parameters", response_model=RiskParametersResponse)
async def update_risk_parameters(updates: RiskParametersUpdate):
    """Update risk management parameters"""
    try:
        from src.config import get_config, update_config_values
        
        config = get_config()
        config_updates = {}
        
        # Validate component weights sum to 1.0 if all provided
        weights_provided = all([
            updates.risk_volatility_weight is not None,
            updates.risk_proximity_weight is not None,
            updates.risk_trend_strength_weight is not None
        ])
        
        if weights_provided:
            total = (updates.risk_volatility_weight + 
                    updates.risk_proximity_weight + 
                    updates.risk_trend_strength_weight)
            if abs(total - 1.0) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Risk component weights must sum to 1.0, got {total:.3f}"
                )
        
        # Risk Component Weights
        if updates.risk_volatility_weight is not None:
            config_updates["RISK_VOLATILITY_WEIGHT"] = updates.risk_volatility_weight
        if updates.risk_proximity_weight is not None:
            config_updates["RISK_PROXIMITY_WEIGHT"] = updates.risk_proximity_weight
        if updates.risk_trend_strength_weight is not None:
            config_updates["RISK_TREND_STRENGTH_WEIGHT"] = updates.risk_trend_strength_weight
        
        # Stop-Loss / Take-Profit Multipliers
        if updates.stop_loss_sr_buffer is not None:
            config_updates["STOP_LOSS_SR_BUFFER"] = updates.stop_loss_sr_buffer
        if updates.stop_loss_atr_mult is not None:
            config_updates["STOP_LOSS_ATR_MULTIPLIER"] = updates.stop_loss_atr_mult
        if updates.take_profit_atr_mult is not None:
            config_updates["TAKE_PROFIT_ATR_MULTIPLIER"] = updates.take_profit_atr_mult
        
        # S/R Distance Thresholds
        if updates.sr_support_max_distance_pct is not None:
            config_updates["SR_SUPPORT_MAX_DISTANCE_PCT"] = updates.sr_support_max_distance_pct
        if updates.sr_resistance_max_distance_pct is not None:
            config_updates["SR_RESISTANCE_MAX_DISTANCE_PCT"] = updates.sr_resistance_max_distance_pct
        
        # S/R DBSCAN Parameters
        if updates.sr_dbscan_eps is not None:
            config_updates["SR_DBSCAN_EPS"] = updates.sr_dbscan_eps
        if updates.sr_dbscan_min_samples is not None:
            config_updates["SR_DBSCAN_MIN_SAMPLES"] = updates.sr_dbscan_min_samples
        if updates.sr_dbscan_order is not None:
            config_updates["SR_DBSCAN_ORDER"] = updates.sr_dbscan_order
        if updates.sr_dbscan_lookback is not None:
            config_updates["SR_DBSCAN_LOOKBACK"] = updates.sr_dbscan_lookback
        
        if not config_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        update_config_values(config, config_updates)
        
        logger.info(f"Risk parameters updated: {config_updates}")
        
        return await get_risk_parameters()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating risk parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== TECHNICAL COMPONENT WEIGHTS (PERCENTAGE-BASED) =====

class TechnicalComponentWeightsUpdate(BaseModel):
    """Model for updating technical component percentage weights"""
    tech_sma_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_rsi_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_macd_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_bollinger_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_stochastic_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_volume_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_cci_weight: Optional[float] = Field(None, ge=0, le=1)
    tech_adx_weight: Optional[float] = Field(None, ge=0, le=1)

class TechnicalComponentWeightsResponse(BaseModel):
    """Response model for technical component percentage weights"""
    tech_sma_weight: float
    tech_rsi_weight: float
    tech_macd_weight: float
    tech_bollinger_weight: float
    tech_stochastic_weight: float
    tech_volume_weight: float
    tech_cci_weight: float
    tech_adx_weight: float

@router.get("/technical-component-weights", response_model=TechnicalComponentWeightsResponse)
async def get_technical_component_weights():
    """Get current technical component percentage weights"""
    try:
        from src.config import get_config
        config = get_config()
        
        return TechnicalComponentWeightsResponse(
            tech_sma_weight=config.tech_sma_weight,
            tech_rsi_weight=config.tech_rsi_weight,
            tech_macd_weight=config.tech_macd_weight,
            tech_bollinger_weight=config.tech_bollinger_weight,
            tech_stochastic_weight=config.tech_stochastic_weight,
            tech_volume_weight=config.tech_volume_weight,
            tech_cci_weight=config.tech_cci_weight,
            tech_adx_weight=config.tech_adx_weight
        )
    except Exception as e:
        logger.error(f"Error getting technical component weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/technical-component-weights", response_model=TechnicalComponentWeightsResponse)
async def update_technical_component_weights(updates: TechnicalComponentWeightsUpdate):
    """Update technical component percentage weights"""
    try:
        from src.config import get_config, update_config_values
        
        config = get_config()
        config_updates = {}
        
        # Check if all weights provided and sum to 1.0
        weights = [
            updates.tech_sma_weight,
            updates.tech_rsi_weight,
            updates.tech_macd_weight,
            updates.tech_bollinger_weight,
            updates.tech_stochastic_weight,
            updates.tech_volume_weight,
            updates.tech_cci_weight,
            updates.tech_adx_weight
        ]
        
        if all(w is not None for w in weights):
            total = sum(weights)
            if abs(total - 1.0) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Technical component weights must sum to 1.0 (100%), got {total:.3f}"
                )
        
        if updates.tech_sma_weight is not None:
            config_updates["TECH_SMA_WEIGHT"] = updates.tech_sma_weight
        if updates.tech_rsi_weight is not None:
            config_updates["TECH_RSI_WEIGHT"] = updates.tech_rsi_weight
        if updates.tech_macd_weight is not None:
            config_updates["TECH_MACD_WEIGHT"] = updates.tech_macd_weight
        if updates.tech_bollinger_weight is not None:
            config_updates["TECH_BOLLINGER_WEIGHT"] = updates.tech_bollinger_weight
        if updates.tech_stochastic_weight is not None:
            config_updates["TECH_STOCHASTIC_WEIGHT"] = updates.tech_stochastic_weight
        if updates.tech_volume_weight is not None:
            config_updates["TECH_VOLUME_WEIGHT"] = updates.tech_volume_weight
        if updates.tech_cci_weight is not None:
            config_updates["TECH_CCI_WEIGHT"] = updates.tech_cci_weight
        if updates.tech_adx_weight is not None:
            config_updates["TECH_ADX_WEIGHT"] = updates.tech_adx_weight
        
        if not config_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        update_config_values(config, config_updates)
        
        logger.info(f"Technical component weights updated: {config_updates}")
        
        return await get_technical_component_weights()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating technical component weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ===== ADVANCED SIGNAL PARAMETERS =====

class AdvancedSignalParamsUpdate(BaseModel):
    """RSI/Stochastic zones + Alignment bonus + Setup quality"""
    # RSI zones
    rsi_overbought: Optional[int] = Field(None, ge=60, le=90)
    rsi_oversold: Optional[int] = Field(None, ge=10, le=40)
    rsi_neutral_low: Optional[int] = Field(None, ge=30, le=55)
    rsi_neutral_high: Optional[int] = Field(None, ge=45, le=70)
    # Stochastic zones
    stoch_overbought: Optional[int] = Field(None, ge=60, le=95)
    stoch_oversold: Optional[int] = Field(None, ge=5, le=40)
    # S/R level filtering
    sr_min_distance_pct: Optional[float] = Field(None, ge=0.1, le=5.0)
    sr_top_n_levels: Optional[int] = Field(None, ge=1, le=20)
    # Alignment bonus thresholds
    alignment_tech_threshold: Optional[int] = Field(None, ge=20, le=80)
    alignment_sent_threshold: Optional[int] = Field(None, ge=20, le=80)
    alignment_risk_threshold: Optional[int] = Field(None, ge=20, le=80)
    alignment_bonus_all: Optional[int] = Field(None, ge=0, le=20)
    alignment_bonus_tr: Optional[int] = Field(None, ge=0, le=15)
    alignment_bonus_st: Optional[int] = Field(None, ge=0, le=15)
    alignment_bonus_sr: Optional[int] = Field(None, ge=0, le=15)
    # Setup quality thresholds
    setup_stop_min_pct: Optional[float] = Field(None, ge=0.5, le=5.0)
    setup_stop_max_pct: Optional[float] = Field(None, ge=2.0, le=15.0)
    setup_target_min_pct: Optional[float] = Field(None, ge=1.0, le=10.0)
    setup_stop_hard_max_pct: Optional[float] = Field(None, ge=5.0, le=20.0)
    setup_target_hard_min_pct: Optional[float] = Field(None, ge=0.5, le=5.0)

class AdvancedSignalParamsResponse(BaseModel):
    rsi_overbought: int
    rsi_oversold: int
    rsi_neutral_low: int
    rsi_neutral_high: int
    stoch_overbought: int
    stoch_oversold: int
    sr_min_distance_pct: float
    sr_top_n_levels: int
    alignment_tech_threshold: int
    alignment_sent_threshold: int
    alignment_risk_threshold: int
    alignment_bonus_all: int
    alignment_bonus_tr: int
    alignment_bonus_st: int
    alignment_bonus_sr: int
    setup_stop_min_pct: float
    setup_stop_max_pct: float
    setup_target_min_pct: float
    setup_stop_hard_max_pct: float
    setup_target_hard_min_pct: float

@router.get("/advanced-signal", response_model=AdvancedSignalParamsResponse)
async def get_advanced_signal_params():
    try:
        from src.config import get_config
        c = get_config()
        return AdvancedSignalParamsResponse(
            rsi_overbought=c.rsi_overbought, rsi_oversold=c.rsi_oversold,
            rsi_neutral_low=c.rsi_neutral_low, rsi_neutral_high=c.rsi_neutral_high,
            stoch_overbought=c.stoch_overbought, stoch_oversold=c.stoch_oversold,
            sr_min_distance_pct=c.sr_min_distance_pct, sr_top_n_levels=c.sr_top_n_levels,
            alignment_tech_threshold=c.alignment_tech_threshold,
            alignment_sent_threshold=c.alignment_sent_threshold,
            alignment_risk_threshold=c.alignment_risk_threshold,
            alignment_bonus_all=c.alignment_bonus_all, alignment_bonus_tr=c.alignment_bonus_tr,
            alignment_bonus_st=c.alignment_bonus_st, alignment_bonus_sr=c.alignment_bonus_sr,
            setup_stop_min_pct=c.setup_stop_min_pct, setup_stop_max_pct=c.setup_stop_max_pct,
            setup_target_min_pct=c.setup_target_min_pct,
            setup_stop_hard_max_pct=c.setup_stop_hard_max_pct,
            setup_target_hard_min_pct=c.setup_target_hard_min_pct,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/advanced-signal", response_model=AdvancedSignalParamsResponse)
async def update_advanced_signal_params(updates: AdvancedSignalParamsUpdate):
    try:
        from src.config import get_config, update_config_values
        config_updates = {}
        for field, key in [
            ("rsi_overbought", "RSI_OVERBOUGHT"), ("rsi_oversold", "RSI_OVERSOLD"),
            ("rsi_neutral_low", "RSI_NEUTRAL_LOW"), ("rsi_neutral_high", "RSI_NEUTRAL_HIGH"),
            ("stoch_overbought", "STOCH_OVERBOUGHT"), ("stoch_oversold", "STOCH_OVERSOLD"),
            ("sr_min_distance_pct", "SR_MIN_DISTANCE_PCT"), ("sr_top_n_levels", "SR_TOP_N_LEVELS"),
            ("alignment_tech_threshold", "ALIGNMENT_TECH_THRESHOLD"),
            ("alignment_sent_threshold", "ALIGNMENT_SENT_THRESHOLD"),
            ("alignment_risk_threshold", "ALIGNMENT_RISK_THRESHOLD"),
            ("alignment_bonus_all", "ALIGNMENT_BONUS_ALL"), ("alignment_bonus_tr", "ALIGNMENT_BONUS_TR"),
            ("alignment_bonus_st", "ALIGNMENT_BONUS_ST"), ("alignment_bonus_sr", "ALIGNMENT_BONUS_SR"),
            ("setup_stop_min_pct", "SETUP_STOP_MIN_PCT"), ("setup_stop_max_pct", "SETUP_STOP_MAX_PCT"),
            ("setup_target_min_pct", "SETUP_TARGET_MIN_PCT"),
            ("setup_stop_hard_max_pct", "SETUP_STOP_HARD_MAX_PCT"),
            ("setup_target_hard_min_pct", "SETUP_TARGET_HARD_MIN_PCT"),
        ]:
            v = getattr(updates, field)
            if v is not None:
                config_updates[key] = v
        if not config_updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        update_config_values(get_config(), config_updates)
        return await get_advanced_signal_params()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== ADVANCED RISK / SCORING PARAMETERS =====

class AdvancedRiskScoringUpdate(BaseModel):
    """ATR volatility scaling + ADX trend strength scaling"""
    # ATR volatility scaling breakpoints
    atr_vol_very_low: Optional[float] = Field(None, ge=0.5, le=3.0)
    atr_vol_low: Optional[float] = Field(None, ge=1.0, le=4.0)
    atr_vol_moderate: Optional[float] = Field(None, ge=2.0, le=6.0)
    atr_vol_high: Optional[float] = Field(None, ge=3.0, le=10.0)
    # ADX trend strength breakpoints
    adx_very_strong: Optional[int] = Field(None, ge=30, le=60)
    adx_strong: Optional[int] = Field(None, ge=20, le=50)
    adx_moderate: Optional[int] = Field(None, ge=15, le=40)
    adx_weak: Optional[int] = Field(None, ge=10, le=35)
    adx_very_weak: Optional[int] = Field(None, ge=5, le=25)

class AdvancedRiskScoringResponse(BaseModel):
    atr_vol_very_low: float
    atr_vol_low: float
    atr_vol_moderate: float
    atr_vol_high: float
    adx_very_strong: int
    adx_strong: int
    adx_moderate: int
    adx_weak: int
    adx_very_weak: int

@router.get("/advanced-risk-scoring", response_model=AdvancedRiskScoringResponse)
async def get_advanced_risk_scoring():
    try:
        from src.config import get_config
        c = get_config()
        return AdvancedRiskScoringResponse(
            atr_vol_very_low=c.atr_vol_very_low, atr_vol_low=c.atr_vol_low,
            atr_vol_moderate=c.atr_vol_moderate, atr_vol_high=c.atr_vol_high,
            adx_very_strong=c.adx_very_strong, adx_strong=c.adx_strong,
            adx_moderate=c.adx_moderate, adx_weak=c.adx_weak, adx_very_weak=c.adx_very_weak,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/advanced-risk-scoring", response_model=AdvancedRiskScoringResponse)
async def update_advanced_risk_scoring(updates: AdvancedRiskScoringUpdate):
    try:
        from src.config import get_config, update_config_values
        config_updates = {}
        for field, key in [
            ("atr_vol_very_low", "ATR_VOL_VERY_LOW"), ("atr_vol_low", "ATR_VOL_LOW"),
            ("atr_vol_moderate", "ATR_VOL_MODERATE"), ("atr_vol_high", "ATR_VOL_HIGH"),
            ("adx_very_strong", "ADX_VERY_STRONG"), ("adx_strong", "ADX_STRONG"),
            ("adx_moderate", "ADX_MODERATE"), ("adx_weak", "ADX_WEAK"),
            ("adx_very_weak", "ADX_VERY_WEAK"),
        ]:
            v = getattr(updates, field)
            if v is not None:
                config_updates[key] = v
        if not config_updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        update_config_values(get_config(), config_updates)
        return await get_advanced_risk_scoring()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== ADVANCED CONFIDENCE PARAMETERS =====

class AdvancedConfidenceUpdate(BaseModel):
    """Technical confidence calculation + Sentiment confidence parameters"""
    # Technical confidence
    tech_conf_rsi_bullish: Optional[int] = Field(None, ge=50, le=70)
    tech_conf_rsi_bearish: Optional[int] = Field(None, ge=30, le=50)
    tech_conf_adx_strong: Optional[int] = Field(None, ge=15, le=40)
    tech_conf_adx_moderate: Optional[int] = Field(None, ge=10, le=30)
    tech_conf_adx_strong_boost: Optional[float] = Field(None, ge=0.0, le=0.3)
    tech_conf_adx_moderate_boost: Optional[float] = Field(None, ge=0.0, le=0.2)
    tech_conf_base: Optional[float] = Field(None, ge=0.3, le=0.7)
    tech_conf_alignment_weight: Optional[float] = Field(None, ge=0.1, le=0.5)
    tech_conf_max: Optional[float] = Field(None, ge=0.7, le=1.0)
    # Sentiment confidence
    sentiment_conf_full_news_count: Optional[int] = Field(None, ge=3, le=30)
    sentiment_conf_high_news_count: Optional[int] = Field(None, ge=2, le=20)
    sentiment_conf_med_news_count: Optional[int] = Field(None, ge=1, le=10)
    sentiment_conf_low_news_count: Optional[int] = Field(None, ge=1, le=5)
    sentiment_positive_threshold: Optional[float] = Field(None, ge=0.05, le=0.5)
    sentiment_negative_threshold: Optional[float] = Field(None, ge=-0.5, le=-0.05)

class AdvancedConfidenceResponse(BaseModel):
    tech_conf_rsi_bullish: int
    tech_conf_rsi_bearish: int
    tech_conf_adx_strong: int
    tech_conf_adx_moderate: int
    tech_conf_adx_strong_boost: float
    tech_conf_adx_moderate_boost: float
    tech_conf_base: float
    tech_conf_alignment_weight: float
    tech_conf_max: float
    sentiment_conf_full_news_count: int
    sentiment_conf_high_news_count: int
    sentiment_conf_med_news_count: int
    sentiment_conf_low_news_count: int
    sentiment_positive_threshold: float
    sentiment_negative_threshold: float

@router.get("/advanced-confidence", response_model=AdvancedConfidenceResponse)
async def get_advanced_confidence():
    try:
        from src.config import get_config
        c = get_config()
        return AdvancedConfidenceResponse(
            tech_conf_rsi_bullish=c.tech_conf_rsi_bullish,
            tech_conf_rsi_bearish=c.tech_conf_rsi_bearish,
            tech_conf_adx_strong=c.tech_conf_adx_strong,
            tech_conf_adx_moderate=c.tech_conf_adx_moderate,
            tech_conf_adx_strong_boost=c.tech_conf_adx_strong_boost,
            tech_conf_adx_moderate_boost=c.tech_conf_adx_moderate_boost,
            tech_conf_base=c.tech_conf_base,
            tech_conf_alignment_weight=c.tech_conf_alignment_weight,
            tech_conf_max=c.tech_conf_max,
            sentiment_conf_full_news_count=c.sentiment_conf_full_news_count,
            sentiment_conf_high_news_count=c.sentiment_conf_high_news_count,
            sentiment_conf_med_news_count=c.sentiment_conf_med_news_count,
            sentiment_conf_low_news_count=c.sentiment_conf_low_news_count,
            sentiment_positive_threshold=c.sentiment_positive_threshold,
            sentiment_negative_threshold=c.sentiment_negative_threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/advanced-confidence", response_model=AdvancedConfidenceResponse)
async def update_advanced_confidence(updates: AdvancedConfidenceUpdate):
    try:
        from src.config import get_config, update_config_values
        config_updates = {}
        for field, key in [
            ("tech_conf_rsi_bullish", "TECH_CONF_RSI_BULLISH"),
            ("tech_conf_rsi_bearish", "TECH_CONF_RSI_BEARISH"),
            ("tech_conf_adx_strong", "TECH_CONF_ADX_STRONG"),
            ("tech_conf_adx_moderate", "TECH_CONF_ADX_MODERATE"),
            ("tech_conf_adx_strong_boost", "TECH_CONF_ADX_STRONG_BOOST"),
            ("tech_conf_adx_moderate_boost", "TECH_CONF_ADX_MODERATE_BOOST"),
            ("tech_conf_base", "TECH_CONF_BASE"),
            ("tech_conf_alignment_weight", "TECH_CONF_ALIGNMENT_WEIGHT"),
            ("tech_conf_max", "TECH_CONF_MAX"),
            ("sentiment_conf_full_news_count", "SENTIMENT_CONF_FULL_NEWS_COUNT"),
            ("sentiment_conf_high_news_count", "SENTIMENT_CONF_HIGH_NEWS_COUNT"),
            ("sentiment_conf_med_news_count", "SENTIMENT_CONF_MED_NEWS_COUNT"),
            ("sentiment_conf_low_news_count", "SENTIMENT_CONF_LOW_NEWS_COUNT"),
            ("sentiment_positive_threshold", "SENTIMENT_POSITIVE_THRESHOLD"),
            ("sentiment_negative_threshold", "SENTIMENT_NEGATIVE_THRESHOLD"),
        ]:
            v = getattr(updates, field)
            if v is not None:
                config_updates[key] = v
        if not config_updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        update_config_values(get_config(), config_updates)
        return await get_advanced_confidence()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
