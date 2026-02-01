import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiArrowLeft, FiSave, FiEdit2, FiTrash2, FiPlus } from 'react-icons/fi';


// Timeframe and Lookback options
const TIMEFRAME_OPTIONS = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
  { value: '1d', label: '1d' },
];

const LOOKBACK_OPTIONS = [
  { value: '1d', label: '1d' },
  { value: '2d', label: '2d' },
  { value: '3d', label: '3d' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: '180d', label: '180d' },
];

function RiskTab({ params, setParams }: any) {
  return (
    <div>
      {/* Risk Component Weights */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          ⚖️ Risk Component Weights
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Configure how risk components are weighted (must sum to 100%)
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
          {/* Volatility Weight */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              🌡️ Volatility (ATR)
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="number"
                min="0"
                max="100"
                value={params.volatilityWeight}
                onChange={(e) => setParams({ ...params, volatilityWeight: parseInt(e.target.value) || 0 })}
                style={{
                  width: '80px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
              <span style={{ color: '#94a3b8', fontSize: '14px' }}>%</span>
            </div>
          </div>

          {/* Proximity Weight */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              📍 S/R Proximity
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="number"
                min="0"
                max="100"
                value={params.proximityWeight}
                onChange={(e) => setParams({ ...params, proximityWeight: parseInt(e.target.value) || 0 })}
                style={{
                  width: '80px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
              <span style={{ color: '#94a3b8', fontSize: '14px' }}>%</span>
            </div>
          </div>

          {/* Trend Strength Weight */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              💪 Trend Strength (ADX)
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="number"
                min="0"
                max="100"
                value={params.trendStrengthWeight}
                onChange={(e) => setParams({ ...params, trendStrengthWeight: parseInt(e.target.value) || 0 })}
                style={{
                  width: '80px',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
              <span style={{ color: '#94a3b8', fontSize: '14px' }}>%</span>
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: 'rgba(59, 130, 246, 0.1)',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#94a3b8'
        }}>
          ℹ️ Total: {params.volatilityWeight + params.proximityWeight + params.trendStrengthWeight}% 
          {(params.volatilityWeight + params.proximityWeight + params.trendStrengthWeight) !== 100 && 
            <span style={{ color: '#ef4444', marginLeft: '8px' }}>⚠️ Must sum to 100%</span>
          }
        </div>
      </div>

      {/* Stop-Loss / Take-Profit Multipliers */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          🎯 Stop-Loss / Take-Profit Calculation
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          ATR-based multipliers for stop-loss and take-profit levels
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
          {/* S/R Buffer */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              S/R Buffer (×ATR)
            </label>
            <input
              type="number"
              min="0.1"
              max="2.0"
              step="0.1"
              value={params.stopLossSrBuffer}
              onChange={(e) => setParams({ ...params, stopLossSrBuffer: parseFloat(e.target.value) || 0.5 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Buffer below support (default: 0.5×)
            </div>
          </div>

          {/* Stop-Loss ATR Multiplier */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Stop-Loss (×ATR)
            </label>
            <input
              type="number"
              min="0.5"
              max="5.0"
              step="0.5"
              value={params.stopLossAtrMult}
              onChange={(e) => setParams({ ...params, stopLossAtrMult: parseFloat(e.target.value) || 2.0 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              ATR-based stop (default: 2×)
            </div>
          </div>

          {/* Take-Profit ATR Multiplier */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Take-Profit (×ATR)
            </label>
            <input
              type="number"
              min="1.0"
              max="10.0"
              step="0.5"
              value={params.takeProfitAtrMult}
              onChange={(e) => setParams({ ...params, takeProfitAtrMult: parseFloat(e.target.value) || 3.0 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              ATR-based target (default: 3×)
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: 'rgba(59, 130, 246, 0.1)',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#94a3b8'
        }}>
          ℹ️ Risk:Reward Ratio: 1:{(params.takeProfitAtrMult / params.stopLossAtrMult).toFixed(2)}
          {(params.takeProfitAtrMult / params.stopLossAtrMult) < 1.5 && 
            <span style={{ color: '#f59e0b', marginLeft: '8px' }}>⚠️ R:R below 1:1.5 (risky)</span>
          }
        </div>
      </div>

      {/* S/R Distance Thresholds */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          📏 S/R Distance Thresholds
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Maximum distance to use support/resistance levels (otherwise use ATR fallback)
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* Support Max Distance */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Support Max Distance (%)
            </label>
            <input
              type="number"
              min="1"
              max="20"
              step="0.5"
              value={params.srSupportMaxDistPct}
              onChange={(e) => setParams({ ...params, srSupportMaxDistPct: parseFloat(e.target.value) || 5.0 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Max % below price for stop-loss (default: 5%)
            </div>
          </div>

          {/* Resistance Max Distance */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Resistance Max Distance (%)
            </label>
            <input
              type="number"
              min="1"
              max="20"
              step="0.5"
              value={params.srResistanceMaxDistPct}
              onChange={(e) => setParams({ ...params, srResistanceMaxDistPct: parseFloat(e.target.value) || 8.0 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Max % above price for take-profit (default: 8%)
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: 'rgba(59, 130, 246, 0.1)',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#94a3b8'
        }}>
          ℹ️ If S/R is beyond these distances, ATR-based fallback is used instead
        </div>
      </div>

      {/* S/R DBSCAN Detection Parameters */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        marginTop: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          🔍 S/R Detection (DBSCAN)
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Advanced parameters for support/resistance level detection
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* EPS (Clustering Proximity) */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Clustering Distance (EPS) %
            </label>
            <input
              type="number"
              min="1"
              max="10"
              step="0.5"
              value={params.srDbscanEps}
              onChange={(e) => setParams({ ...params, srDbscanEps: parseFloat(e.target.value) || 4.0 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Pivot points within EPS% clustered together (default: 4%)
            </div>
          </div>

          {/* Min Samples */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Min Cluster Size
            </label>
            <input
              type="number"
              min="2"
              max="10"
              value={params.srDbscanMinSamples}
              onChange={(e) => setParams({ ...params, srDbscanMinSamples: parseInt(e.target.value) || 3 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Minimum pivots to form valid S/R level (default: 3)
            </div>
          </div>

          {/* Pivot Order */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Pivot Order (bars)
            </label>
            <input
              type="number"
              min="3"
              max="14"
              value={params.srDbscanOrder}
              onChange={(e) => setParams({ ...params, srDbscanOrder: parseInt(e.target.value) || 7 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Bars on each side for pivot detection (default: 7)
            </div>
          </div>

          {/* Lookback Days */}
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
              Lookback Period (days)
            </label>
            <input
              type="number"
              min="30"
              max="365"
              step="30"
              value={params.srDbscanLookback}
              onChange={(e) => setParams({ ...params, srDbscanLookback: parseInt(e.target.value) || 180 })}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(15, 23, 42, 0.6)',
                color: '#f1f5f9',
                fontSize: '14px'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Historical data window (default: 180 days = 6 months)
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: 'rgba(59, 130, 246, 0.1)',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#94a3b8'
        }}>
          💡 Higher EPS = Fewer, broader S/R zones | Higher min_samples = Stronger, tested levels<br/>
          💡 Higher order = Smoother pivots | Longer lookback = More significant long-term levels
        </div>
      </div>

    </div>
  );
}

export function Configuration() {
  const [activeTab, setActiveTab] = useState(0);
  const [showTickerModal, setShowTickerModal] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Mock data (later connect to API)
  const [tickers] = useState([
    { symbol: 'OTP.BD', name: 'OTP Bank Nyrt.', market: 'BÉT', priority: 'high', active: true },
    { symbol: 'MOL.BD', name: 'MOL Magyar Olaj', market: 'BÉT', priority: 'medium', active: true },
    { symbol: 'RICHTER', name: 'Richter Gedeon', market: 'BÉT', priority: 'low', active: true },
  ]);

  const [sentimentWeights, setSentimentWeights] = useState({
    fresh_0_2h: 100,
    strong_2_6h: 85,
    intraday_6_12h: 60,
    overnight_12_24h: 35,
  });

  const [componentWeights, setComponentWeights] = useState({
    sentiment: 70,
    technical: 20,
    risk: 10,
  });

  const [thresholds, setThresholds] = useState({
    strongBuyScore: 65,
    strongBuyConfidence: 0.75,
    moderateBuyScore: 50,
    moderateBuyConfidence: 0.65,
    strongSellScore: -65,
    strongSellConfidence: 0.75,
    moderateSellScore: -50,
    moderateSellConfidence: 0.65,
  });

  const [technicalWeights, setTechnicalWeights] = useState({
    sma20Bullish: 25,
    sma20Bearish: 15,
    sma50Bullish: 20,
    sma50Bearish: 10,
    goldenCross: 15,
    deathCross: 15,
    rsiNeutral: 20,
    rsiBullish: 30,
    rsiWeakBullish: 10,
    rsiOverbought: 20,
    rsiOversold: 15,  // Bullish reversal (not 20)
  })

  // ===== INDICATOR PARAMETERS STATE =====
  const [indicatorParams, setIndicatorParams] = useState({
    rsiPeriod: 14, rsiTimeframe: '5m', rsiLookback: '2d',
    smaShortPeriod: 20, smaShortTimeframe: '5m', smaShortLookback: '2d',
    smaMediumPeriod: 50, smaMediumTimeframe: '1h', smaMediumLookback: '30d',
    smaLongPeriod: 200, smaLongTimeframe: '1d', smaLongLookback: '180d',
    macdFast: 12, macdSlow: 26, macdSignal: 9, macdTimeframe: '15m', macdLookback: '3d',
    bbPeriod: 20, bbStdDev: 2.0, bbTimeframe: '1h', bbLookback: '7d',
    atrPeriod: 14, atrTimeframe: '1d', atrLookback: '180d',
    stochPeriod: 14, stochTimeframe: '15m', stochLookback: '3d',
    adxPeriod: 14, adxTimeframe: '1h', adxLookback: '30d',
  })

  // ===== RISK PARAMETERS STATE =====
  const [riskParams, setRiskParams] = useState({
    // Risk Component Weights
    volatilityWeight: 40,
    proximityWeight: 35,
    trendStrengthWeight: 25,
    // Stop-Loss / Take-Profit
    stopLossSrBuffer: 0.5,
    stopLossAtrMult: 2.0,
    takeProfitAtrMult: 3.0,
    // S/R Distance Thresholds
    srSupportMaxDistPct: 5.0,
    srResistanceMaxDistPct: 8.0,
    // DBSCAN S/R Detection
    srDbscanEps: 4.0,
    srDbscanMinSamples: 3,
    srDbscanOrder: 7,
    srDbscanLookback: 180,
  });;;

  // ===== LOAD CONFIG FROM BACKEND ON MOUNT =====
  useEffect(() => {
    loadConfigFromBackend();
  }, []);

  const loadConfigFromBackend = async () => {
    try {
      // Load signal weights and thresholds
      const response = await fetch('http://localhost:8000/api/v1/config/signal');
      if (response.ok) {
        const config = await response.json();
        setComponentWeights({
          sentiment: Math.round(config.sentiment_weight * 100),
          technical: Math.round(config.technical_weight * 100),
          risk: Math.round(config.risk_weight * 100),
        });
        setThresholds({
          strongBuyScore: config.strong_buy_score,
          strongBuyConfidence: config.strong_buy_confidence,
          moderateBuyScore: config.moderate_buy_score,
          moderateBuyConfidence: config.moderate_buy_confidence,
          strongSellScore: config.strong_sell_score,
          strongSellConfidence: config.strong_sell_confidence,
          moderateSellScore: config.moderate_sell_score,
          moderateSellConfidence: config.moderate_sell_confidence,
        });
        console.log('✅ Signal config loaded:', config);
      }
      
      // Load decay weights
      const decayResponse = await fetch('http://localhost:8000/api/v1/config/decay');
      if (decayResponse.ok) {
        const decayConfig = await decayResponse.json();
        setSentimentWeights({
          fresh_0_2h: decayConfig.fresh_0_2h,
          strong_2_6h: decayConfig.strong_2_6h,
          intraday_6_12h: decayConfig.intraday_6_12h,
          overnight_12_24h: decayConfig.overnight_12_24h,
        });
        console.log('✅ Decay weights loaded:', decayConfig);
      }

      // Load technical weights
      const techResponse = await fetch('http://localhost:8000/api/v1/config/technical-weights');
      if (techResponse.ok) {
        const techConfig = await techResponse.json();
        setTechnicalWeights({
          sma20Bullish: techConfig.tech_sma20_bullish,
          sma20Bearish: techConfig.tech_sma20_bearish,
          sma50Bullish: techConfig.tech_sma50_bullish,
          sma50Bearish: techConfig.tech_sma50_bearish,
          goldenCross: techConfig.tech_golden_cross,
          deathCross: techConfig.tech_death_cross,
          rsiNeutral: techConfig.tech_rsi_neutral,
          rsiBullish: techConfig.tech_rsi_bullish,
          rsiWeakBullish: techConfig.tech_rsi_weak_bullish,
          rsiOverbought: techConfig.tech_rsi_overbought,
          rsiOversold: techConfig.tech_rsi_oversold,
        });
        console.log('✅ Technical weights loaded:', techConfig);

      // ===== NEW: Load indicator parameters =====
      const indicatorResponse = await fetch('http://localhost:8000/api/v1/config/indicator-parameters');
      if (indicatorResponse.ok) {
        const ic = await indicatorResponse.json();
        setIndicatorParams({
          rsiPeriod: ic.rsi_period, rsiTimeframe: ic.rsi_timeframe, rsiLookback: ic.rsi_lookback,
          smaShortPeriod: ic.sma_short_period, smaShortTimeframe: ic.sma_short_timeframe, smaShortLookback: ic.sma_short_lookback,
          smaMediumPeriod: ic.sma_medium_period, smaMediumTimeframe: ic.sma_medium_timeframe, smaMediumLookback: ic.sma_medium_lookback,
          smaLongPeriod: ic.sma_long_period, smaLongTimeframe: ic.sma_long_timeframe, smaLongLookback: ic.sma_long_lookback,
          macdFast: ic.macd_fast, macdSlow: ic.macd_slow, macdSignal: ic.macd_signal, macdTimeframe: ic.macd_timeframe, macdLookback: ic.macd_lookback,
          bbPeriod: ic.bb_period, bbStdDev: ic.bb_std_dev, bbTimeframe: ic.bb_timeframe, bbLookback: ic.bb_lookback,
          atrPeriod: ic.atr_period, atrTimeframe: ic.atr_timeframe, atrLookback: ic.atr_lookback,
          stochPeriod: ic.stoch_period, stochTimeframe: ic.stoch_timeframe, stochLookback: ic.stoch_lookback,
          adxPeriod: ic.adx_period, adxTimeframe: ic.adx_timeframe, adxLookback: ic.adx_lookback,
        });
        console.log('✅ Indicator parameters loaded:', ic);

      // ===== NEW: Load risk parameters =====
      const riskResponse = await fetch('http://localhost:8000/api/v1/config/risk-parameters');
      if (riskResponse.ok) {
        const rc = await riskResponse.json();
        setRiskParams({
          volatilityWeight: Math.round(rc.risk_volatility_weight * 100),
          proximityWeight: Math.round(rc.risk_proximity_weight * 100),
          trendStrengthWeight: Math.round(rc.risk_trend_strength_weight * 100),
          stopLossSrBuffer: rc.stop_loss_sr_buffer,
          stopLossAtrMult: rc.stop_loss_atr_mult,
          takeProfitAtrMult: rc.take_profit_atr_mult,
          srSupportMaxDistPct: rc.sr_support_max_distance_pct,
          srResistanceMaxDistPct: rc.sr_resistance_max_distance_pct,
          srDbscanEps: rc.sr_dbscan_eps,
          srDbscanMinSamples: rc.sr_dbscan_min_samples,
          srDbscanOrder: rc.sr_dbscan_order,
          srDbscanLookback: rc.sr_dbscan_lookback,
        });
        console.log('✅ Risk parameters loaded:', rc);
      }
      }
      }
    } catch (error) {
      console.error('⚠️ Error loading config:', error);
    }
  };

  const handleSaveAll = async () => {
    setSaving(true);
    
    try {
      // Validate weights sum to 100
      const total = componentWeights.sentiment + componentWeights.technical + componentWeights.risk;
      if (total !== 100) {
        alert(`⚠️ Weights must sum to 100%, currently: ${total}%`);
        setSaving(false);
        return;
      }
      
      // Convert percentages to decimals (0.7, 0.2, 0.1) and add thresholds
      const payload = {
        sentiment_weight: componentWeights.sentiment / 100,
        technical_weight: componentWeights.technical / 100,
        risk_weight: componentWeights.risk / 100,
        strong_buy_score: thresholds.strongBuyScore,
        strong_buy_confidence: thresholds.strongBuyConfidence,
        moderate_buy_score: thresholds.moderateBuyScore,
        moderate_buy_confidence: thresholds.moderateBuyConfidence,
        strong_sell_score: thresholds.strongSellScore,
        strong_sell_confidence: thresholds.strongSellConfidence,
        moderate_sell_score: thresholds.moderateSellScore,
        moderate_sell_confidence: thresholds.moderateSellConfidence,
      };
      
      console.log('📤 Saving config to backend:', payload);
      
      const response = await fetch('http://localhost:8000/api/v1/config/signal', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('✅ Signal config saved:', result);
        
        // Save decay weights too
        const decayPayload = {
          fresh_0_2h: sentimentWeights.fresh_0_2h,
          strong_2_6h: sentimentWeights.strong_2_6h,
          intraday_6_12h: sentimentWeights.intraday_6_12h,
          overnight_12_24h: sentimentWeights.overnight_12_24h,
        };
        
        const decayResponse = await fetch('http://localhost:8000/api/v1/config/decay', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(decayPayload)
        });
        
        if (decayResponse.ok) {
          console.log('✅ Decay weights saved');
        }

        // Save technical weights too
        const techPayload = {
          tech_sma20_bullish: technicalWeights.sma20Bullish,
          tech_sma20_bearish: technicalWeights.sma20Bearish,
          tech_sma50_bullish: technicalWeights.sma50Bullish,
          tech_sma50_bearish: technicalWeights.sma50Bearish,
          tech_golden_cross: technicalWeights.goldenCross,
          tech_death_cross: technicalWeights.deathCross,
          tech_rsi_neutral: technicalWeights.rsiNeutral,
          tech_rsi_bullish: technicalWeights.rsiBullish,
          tech_rsi_weak_bullish: technicalWeights.rsiWeakBullish,
          tech_rsi_overbought: technicalWeights.rsiOverbought,
          tech_rsi_oversold: technicalWeights.rsiOversold,
        };

        const techResponse = await fetch('http://localhost:8000/api/v1/config/technical-weights', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(techPayload)
        });

        if (techResponse.ok) {
          console.log('✅ Technical weights saved');

        // ===== NEW: Save indicator parameters =====
        const ip = indicatorParams;
        const indicatorPayload = {
          rsi_period: ip.rsiPeriod, rsi_timeframe: ip.rsiTimeframe, rsi_lookback: ip.rsiLookback,
          sma_short_period: ip.smaShortPeriod, sma_short_timeframe: ip.smaShortTimeframe, sma_short_lookback: ip.smaShortLookback,
          sma_medium_period: ip.smaMediumPeriod, sma_medium_timeframe: ip.smaMediumTimeframe, sma_medium_lookback: ip.smaMediumLookback,
          sma_long_period: ip.smaLongPeriod, sma_long_timeframe: ip.smaLongTimeframe, sma_long_lookback: ip.smaLongLookback,
          macd_fast: ip.macdFast, macd_slow: ip.macdSlow, macd_signal: ip.macdSignal, macd_timeframe: ip.macdTimeframe, macd_lookback: ip.macdLookback,
          bb_period: ip.bbPeriod, bb_std_dev: ip.bbStdDev, bb_timeframe: ip.bbTimeframe, bb_lookback: ip.bbLookback,
          atr_period: ip.atrPeriod, atr_timeframe: ip.atrTimeframe, atr_lookback: ip.atrLookback,
          stoch_period: ip.stochPeriod, stoch_timeframe: ip.stochTimeframe, stoch_lookback: ip.stochLookback,
          adx_period: ip.adxPeriod, adx_timeframe: ip.adxTimeframe, adx_lookback: ip.adxLookback,
        };

        const indicatorResponse = await fetch('http://localhost:8000/api/v1/config/indicator-parameters', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(indicatorPayload)
        });

        if (indicatorResponse.ok) {
          console.log('✅ Indicator parameters saved');

        // ===== NEW: Save risk parameters =====
        const rp = riskParams;
        
        // Validate weights sum to 100
        const riskWeightTotal = rp.volatilityWeight + rp.proximityWeight + rp.trendStrengthWeight;
        if (riskWeightTotal !== 100) {
          alert(`⚠️ Risk component weights must sum to 100%, currently: ${riskWeightTotal}%`);
          setSaving(false);
          return;
        }
        
        const riskPayload = {
          risk_volatility_weight: rp.volatilityWeight / 100,
          risk_proximity_weight: rp.proximityWeight / 100,
          risk_trend_strength_weight: rp.trendStrengthWeight / 100,
          stop_loss_sr_buffer: rp.stopLossSrBuffer,
          stop_loss_atr_mult: rp.stopLossAtrMult,
          take_profit_atr_mult: rp.takeProfitAtrMult,
          sr_support_max_distance_pct: rp.srSupportMaxDistPct,
          sr_resistance_max_distance_pct: rp.srResistanceMaxDistPct,
          sr_dbscan_eps: rp.srDbscanEps,
          sr_dbscan_min_samples: rp.srDbscanMinSamples,
          sr_dbscan_order: rp.srDbscanOrder,
          sr_dbscan_lookback: rp.srDbscanLookback,
        };

        const riskResponse = await fetch('http://localhost:8000/api/v1/config/risk-parameters', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(riskPayload)
        });

        if (riskResponse.ok) {
          console.log('✅ Risk parameters saved');
        }
        }
        }
        
        // Success notification
        alert('✅ Configuration saved successfully!\n\n' +
              'Signal Weights:\n' +
              `Sentiment: ${componentWeights.sentiment}%\n` +
              `Technical: ${componentWeights.technical}%\n` +
              `Risk: ${componentWeights.risk}%\n\n` +
              'Thresholds:\n' +
              `Strong BUY: Score ≥ ${thresholds.strongBuyScore}, Conf ≥ ${Math.round(thresholds.strongBuyConfidence * 100)}%\n` +
              `Moderate BUY: Score ≥ ${thresholds.moderateBuyScore}, Conf ≥ ${Math.round(thresholds.moderateBuyConfidence * 100)}%\n` +
              `Strong SELL: Score ≤ ${thresholds.strongSellScore}, Conf ≥ ${Math.round(thresholds.strongSellConfidence * 100)}%\n` +
              `Moderate SELL: Score ≤ ${thresholds.moderateSellScore}, Conf ≥ ${Math.round(thresholds.moderateSellConfidence * 100)}%\n\n` +
              'Decay Weights:\n' +
              `0-2h: ${sentimentWeights.fresh_0_2h}%\n` +
              `2-6h: ${sentimentWeights.strong_2_6h}%\n` +
              `6-12h: ${sentimentWeights.intraday_6_12h}%\n` +
              `12-24h: ${sentimentWeights.overnight_12_24h}%`);
        
        // Reload config to verify
        await loadConfigFromBackend();
      } else {
        const error = await response.json();
        console.error('❌ Save failed:', error);
        alert(`❌ Error saving configuration:\n${error.detail || 'Unknown error'}`);
      }
      
    } catch (error) {
      console.error('❌ Error saving config:', error);
      alert('❌ Failed to save configuration.\nCheck console for details.');
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 0, label: '📊 Tickers' },
    { id: 1, label: '📰 News Sources' },
    { id: 2, label: '💭 Sentiment' },
    { id: 3, label: '📈 Technical' },
    { id: 4, label: '🎯 Signals' },
    { id: 5, label: '🛡️ Risk' },
  ];

  const getPriorityBadge = (priority: string) => {
    const styles = {
      high: { bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', text: 'High' },
      medium: { bg: 'rgba(251, 191, 36, 0.2)', color: '#fbbf24', text: 'Medium' },
      low: { bg: 'rgba(100, 116, 139, 0.2)', color: '#94a3b8', text: 'Low' },
    };
    const style = styles[priority as keyof typeof styles] || styles.medium;
    
    return (
      <span style={{
        padding: '4px 10px',
        borderRadius: '6px',
        fontSize: '11px',
        fontWeight: '600',
        textTransform: 'uppercase',
        background: style.bg,
        color: style.color
      }}>
        {style.text}
      </span>
    );
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)',
      color: '#e0e7ff',
      padding: '20px'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 0',
          borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
          marginBottom: '30px',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          <Link to="/" style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#60a5fa',
            textDecoration: 'none',
            fontSize: '14px',
            padding: '8px 16px',
            borderRadius: '8px',
            background: 'rgba(59, 130, 246, 0.1)',
            transition: 'all 0.3s'
          }}>
            <FiArrowLeft /> Dashboard
          </Link>

          <div style={{
            fontSize: '28px',
            fontWeight: '700',
            background: 'linear-gradient(135deg, #3b82f6 0%, #10b981 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            ⚙️ Configuration
          </div>

          <button style={{
            padding: '10px 24px',
            borderRadius: '8px',
            border: 'none',
            fontSize: '14px',
            fontWeight: '600',
            cursor: saving ? 'not-allowed' : 'pointer',
            background: saving 
              ? 'rgba(100, 116, 139, 0.5)' 
              : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            color: 'white',
            transition: 'all 0.3s',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            opacity: saving ? 0.6 : 1
          }}
          onClick={handleSaveAll}
          disabled={saving}
          >
            <FiSave /> {saving ? 'Saving...' : 'Save All Changes'}
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '30px',
          borderBottom: '2px solid rgba(51, 65, 85, 0.5)',
          overflowX: 'auto'
        }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '12px 24px',
                background: 'transparent',
                border: 'none',
                color: activeTab === tab.id ? '#60a5fa' : '#94a3b8',
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.3s',
                borderBottom: activeTab === tab.id ? '3px solid #3b82f6' : '3px solid transparent',
                whiteSpace: 'nowrap'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 0 && <TickersTab tickers={tickers} onAddNew={() => setShowTickerModal(true)} getPriorityBadge={getPriorityBadge} />}
        {activeTab === 1 && <NewsSourcesTab />}
        {activeTab === 2 && <SentimentTab weights={sentimentWeights} setWeights={setSentimentWeights} />}
        {activeTab === 3 && <TechnicalTab weights={technicalWeights} setWeights={setTechnicalWeights} indicatorParams={indicatorParams} setIndicatorParams={setIndicatorParams} />}
        {activeTab === 4 && <SignalsTab componentWeights={componentWeights} setComponentWeights={setComponentWeights} thresholds={thresholds} setThresholds={setThresholds} />}
        {activeTab === 5 && <RiskTab params={riskParams} setParams={setRiskParams} />}

        {/* Add Ticker Modal */}
        {showTickerModal && (
          <div style={{
            position: 'fixed',
            zIndex: 1000,
            left: 0,
            top: 0,
            width: '100%',
            height: '100%',
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onClick={() => setShowTickerModal(false)}
          >
            <div style={{
              background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              borderRadius: '16px',
              padding: '32px',
              maxWidth: '500px',
              width: '90%'
            }}
            onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div style={{ fontSize: '20px', fontWeight: '700', color: '#f1f5f9' }}>+ Add New Ticker</div>
                <button onClick={() => setShowTickerModal(false)} style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '24px', cursor: 'pointer' }}>×</button>
              </div>
              {/* Form content - simplified for MVP */}
              <div style={{ fontSize: '14px', color: '#cbd5e1', marginBottom: '20px' }}>
                Ticker management will be implemented in Phase 2
              </div>
              <button onClick={() => setShowTickerModal(false)} style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(51, 65, 85, 0.5)',
                color: '#cbd5e1',
                cursor: 'pointer'
              }}>Close</button>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

// Tickers Tab Component
function TickersTab({ tickers, onAddNew, getPriorityBadge }: any) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
      border: '1px solid rgba(99, 102, 241, 0.3)',
      borderRadius: '16px',
      padding: '24px'
    }}>
      <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
        📊 Ticker Management
      </div>
      <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
        Manage the stocks you want to track for trading signals
      </div>

      <button onClick={onAddNew} style={{
        padding: '10px 20px',
        borderRadius: '8px',
        border: 'none',
        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
        color: 'white',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
        marginBottom: '20px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <FiPlus /> Add New Ticker
      </button>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
          <thead style={{ background: 'rgba(51, 65, 85, 0.5)' }}>
            <tr>
              {['Ticker', 'Name', 'Market', 'Priority', 'Status', 'Actions'].map((header, idx) => (
                <th key={idx} style={{
                  textAlign: 'left',
                  padding: '12px 16px',
                  fontSize: '12px',
                  fontWeight: '600',
                  color: '#94a3b8',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickers.map((ticker: any, idx: number) => (
              <tr key={idx} style={{ borderBottom: idx < tickers.length - 1 ? '1px solid rgba(51, 65, 85, 0.3)' : 'none' }}>
                <td style={{ padding: '14px 16px' }}>
                  <strong style={{ color: '#60a5fa' }}>{ticker.symbol}</strong>
                </td>
                <td style={{ padding: '14px 16px', fontSize: '14px' }}>{ticker.name}</td>
                <td style={{ padding: '14px 16px', fontSize: '14px' }}>{ticker.market}</td>
                <td style={{ padding: '14px 16px' }}>{getPriorityBadge(ticker.priority)}</td>
                <td style={{ padding: '14px 16px', color: '#10b981' }}>● Active</td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button style={{
                      padding: '6px 10px',
                      borderRadius: '6px',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      background: 'rgba(51, 65, 85, 0.5)',
                      color: '#cbd5e1',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}>
                      <FiEdit2 size={14} />
                    </button>
                    <button style={{
                      padding: '6px 10px',
                      borderRadius: '6px',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      background: 'rgba(51, 65, 85, 0.5)',
                      color: '#cbd5e1',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}>
                      <FiTrash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// News Sources Tab
function NewsSourcesTab() {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
      border: '1px solid rgba(99, 102, 241, 0.3)',
      borderRadius: '16px',
      padding: '24px'
    }}>
      <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
        📰 News Source Configuration
      </div>
      <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
        Configure news sources, credibility weights, and update frequency
      </div>
      <div style={{ fontSize: '14px', color: '#cbd5e1', padding: '40px', textAlign: 'center' }}>
        News source management coming in Phase 2
      </div>
    </div>
  );
}

// Sentiment Tab
function SentimentTab({ weights, setWeights }: any) {
  return (
    <div>
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          💭 Sentiment Decay Model
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Time-based decay weights for day trading optimization
        </div>

        <div style={{
          background: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '8px',
          padding: '14px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          color: '#60a5fa'
        }}>
          <span>ℹ️</span>
          <span>Decay weights determine how much recent news impacts the sentiment score</span>
        </div>

        {[
          { key: 'fresh_0_2h', label: '0-2 hours (Fresh news)', min: 50, max: 100 },
          { key: 'strong_2_6h', label: '2-6 hours (Strong momentum)', min: 20, max: 100 },
          { key: 'intraday_6_12h', label: '6-12 hours (Intraday news)', min: 10, max: 80 },
          { key: 'overnight_12_24h', label: '12-24 hours (Overnight news 🆕)', min: 0, max: 50 },
        ].map(item => (
          <div key={item.key} style={{ margin: '20px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>{item.label}</span>
              <span style={{ fontSize: '16px', fontWeight: '700', color: '#60a5fa' }}>
                {weights[item.key]}%
              </span>
            </div>
            <input
              type="range"
              min={item.min}
              max={item.max}
              value={weights[item.key]}
              onChange={(e) => setWeights({ ...weights, [item.key]: parseInt(e.target.value) })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// Technical Tab
function TechnicalTab({ weights, setWeights, indicatorParams, setIndicatorParams }: any) {
  return (
    <div>
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          📈 Technical Component Weights
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Configure score impact of technical indicators
        </div>

        {/* SMA Trend Weights */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '16px' }}>
            📊 SMA Trend Indicators
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Price &gt; SMA20 (Bullish)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.sma20Bullish}
                onChange={(e) => setWeights({ ...weights, sma20Bullish: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Price &lt; SMA20 (Bearish)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.sma20Bearish}
                onChange={(e) => setWeights({ ...weights, sma20Bearish: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Price &gt; SMA50 (Bullish)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.sma50Bullish}
                onChange={(e) => setWeights({ ...weights, sma50Bullish: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Price &lt; SMA50 (Bearish)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.sma50Bearish}
                onChange={(e) => setWeights({ ...weights, sma50Bearish: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Golden Cross (SMA20 &gt; SMA50)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.goldenCross}
                onChange={(e) => setWeights({ ...weights, goldenCross: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                Death Cross (SMA20 &lt; SMA50)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.deathCross}
                onChange={(e) => setWeights({ ...weights, deathCross: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
          </div>
        </div>

        {/* RSI Weights */}
        <div>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '16px' }}>
            ⚡ RSI (Relative Strength Index)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                RSI Neutral (45-55)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.rsiNeutral}
                onChange={(e) => setWeights({ ...weights, rsiNeutral: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                RSI Bullish (55-70)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.rsiBullish}
                onChange={(e) => setWeights({ ...weights, rsiBullish: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                RSI Weak Bullish (30-45)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.rsiWeakBullish}
                onChange={(e) => setWeights({ ...weights, rsiWeakBullish: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                RSI Overbought (≥70, bearish correction)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.rsiOverbought}
                onChange={(e) => setWeights({ ...weights, rsiOverbought: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>
                RSI Oversold (≤30, bullish reversal)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={weights.rsiOversold}
                onChange={(e) => setWeights({ ...weights, rsiOversold: parseInt(e.target.value) || 0 })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#f1f5f9',
                  fontSize: '14px'
                }}
              />
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '20px',
          padding: '12px',
          background: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#94a3b8'
        }}>
          ℹ️ These values determine how much each indicator affects the technical score. Higher values = stronger influence.<br/>
          <strong>Note:</strong> RSI Overbought subtracts from score (bearish), RSI Oversold adds to score (bullish reversal).
        </div>
      </div>
      {/* ===== INDICATOR PARAMETERS SECTION ===== */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(99, 102, 241, 0.2)',
        padding: '24px',
        marginBottom: '24px',
        marginTop: '32px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          ⚙️ Indicator Periods & Timeframes
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Configure calculation parameters for technical indicators
        </div>

        {/* RSI */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            ⚡ RSI (Relative Strength Index)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="5" max="50" value={indicatorParams.rsiPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, rsiPeriod: parseInt(e.target.value) || 14})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.rsiTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, rsiTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.rsiLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, rsiLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* SMA Short */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            📈 SMA Short
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="5" max="100" value={indicatorParams.smaShortPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaShortPeriod: parseInt(e.target.value) || 20})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.smaShortTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaShortTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.smaShortLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaShortLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* SMA Medium */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            📈 SMA Medium
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="20" max="200" value={indicatorParams.smaMediumPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaMediumPeriod: parseInt(e.target.value) || 50})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.smaMediumTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaMediumTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.smaMediumLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaMediumLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* SMA Long */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            📈 SMA Long
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="100" max="300" value={indicatorParams.smaLongPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaLongPeriod: parseInt(e.target.value) || 200})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.smaLongTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaLongTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.smaLongLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, smaLongLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* MACD */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            📉 MACD
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Fast</label>
              <input type="number" min="5" max="50" value={indicatorParams.macdFast}
                onChange={(e) => setIndicatorParams({...indicatorParams, macdFast: parseInt(e.target.value) || 12})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Slow</label>
              <input type="number" min="10" max="100" value={indicatorParams.macdSlow}
                onChange={(e) => setIndicatorParams({...indicatorParams, macdSlow: parseInt(e.target.value) || 26})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Signal</label>
              <input type="number" min="5" max="50" value={indicatorParams.macdSignal}
                onChange={(e) => setIndicatorParams({...indicatorParams, macdSignal: parseInt(e.target.value) || 9})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.macdTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, macdTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.macdLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, macdLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Bollinger Bands */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            📊 Bollinger Bands
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="10" max="50" value={indicatorParams.bbPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, bbPeriod: parseInt(e.target.value) || 20})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Std Dev</label>
              <input type="number" min="1" max="3" step="0.1" value={indicatorParams.bbStdDev}
                onChange={(e) => setIndicatorParams({...indicatorParams, bbStdDev: parseFloat(e.target.value) || 2.0})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.bbTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, bbTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.bbLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, bbLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* ATR */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            📏 ATR (Average True Range)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="5" max="50" value={indicatorParams.atrPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, atrPeriod: parseInt(e.target.value) || 14})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.atrTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, atrTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.atrLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, atrLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* Stochastic */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            🎯 Stochastic Oscillator
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="5" max="50" value={indicatorParams.stochPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, stochPeriod: parseInt(e.target.value) || 14})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.stochTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, stochTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.stochLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, stochLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* ADX */}
        <div>
          <div style={{ fontSize: '15px', fontWeight: '600', color: '#60a5fa', marginBottom: '12px' }}>
            💪 ADX (Trend Strength)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Period</label>
              <input type="number" min="5" max="50" value={indicatorParams.adxPeriod}
                onChange={(e) => setIndicatorParams({...indicatorParams, adxPeriod: parseInt(e.target.value) || 14})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Timeframe</label>
              <select value={indicatorParams.adxTimeframe}
                onChange={(e) => setIndicatorParams({...indicatorParams, adxTimeframe: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {TIMEFRAME_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Lookback</label>
              <select value={indicatorParams.adxLookback}
                onChange={(e) => setIndicatorParams({...indicatorParams, adxLookback: e.target.value})}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                  background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '13px' }}>
                {LOOKBACK_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        </div>
      </div>
      {/* ===== END INDICATOR PARAMETERS SECTION ===== */}

    </div>
  );
}

// Signals Tab
function SignalsTab({ componentWeights, setComponentWeights, thresholds, setThresholds }: any) {
  return (
    <div>
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          ⚖️ Combined Score Formula
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Customize how sentiment, technical, and risk are combined
        </div>

        <div style={{
          background: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '8px',
          padding: '14px',
          marginBottom: '20px',
          color: '#60a5fa'
        }}>
          ℹ️ Total weight must equal 100%
        </div>

        {[
          { key: 'sentiment', label: 'Sentiment Weight', color: '#10b981' },
          { key: 'technical', label: 'Technical Weight', color: '#3b82f6' },
          { key: 'risk', label: 'Risk Weight', color: '#f59e0b' },
        ].map(item => (
          <div key={item.key} style={{ margin: '20px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>{item.label}</span>
              <span style={{ fontSize: '16px', fontWeight: '700', color: item.color }}>
                {componentWeights[item.key]}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={componentWeights[item.key]}
              onChange={(e) => {
                const newValue = parseInt(e.target.value);
                setComponentWeights({ ...componentWeights, [item.key]: newValue });
              }}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
          </div>
        ))}

        <div style={{ 
          textAlign: 'right', 
          marginTop: '20px', 
          fontSize: '14px',
          color: componentWeights.sentiment + componentWeights.technical + componentWeights.risk === 100 ? '#10b981' : '#ef4444',
          fontWeight: '600'
        }}>
          Total: {componentWeights.sentiment + componentWeights.technical + componentWeights.risk}%
          {componentWeights.sentiment + componentWeights.technical + componentWeights.risk !== 100 && ' ⚠️ Must equal 100%'}
        </div>
      </div>

      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '24px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
          🎯 Signal Decision Thresholds
        </div>
        <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
          Define score and confidence thresholds for signal strength classification
        </div>

        <div style={{
          background: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '8px',
          padding: '14px',
          marginBottom: '20px',
          color: '#60a5fa'
        }}>
          ℹ️ Higher thresholds = Fewer but higher quality signals
        </div>

        {/* BUY Thresholds */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{ fontSize: '16px', fontWeight: '600', color: '#10b981', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🟢</span>
            <span>BUY Signal Thresholds</span>
          </div>

          {/* Strong Buy Score */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Strong Buy Score</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#10b981' }}>
                {thresholds.strongBuyScore}
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={80}
              value={thresholds.strongBuyScore}
              onChange={(e) => setThresholds({ ...thresholds, strongBuyScore: parseInt(e.target.value) })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Combined score must be ≥ this value
            </div>
          </div>

          {/* Strong Buy Confidence */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Strong Buy Confidence</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#10b981' }}>
                {Math.round(thresholds.strongBuyConfidence * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={60}
              max={90}
              value={thresholds.strongBuyConfidence * 100}
              onChange={(e) => setThresholds({ ...thresholds, strongBuyConfidence: parseInt(e.target.value) / 100 })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Overall confidence must be ≥ this value
            </div>
          </div>

          {/* Moderate Buy Score */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Moderate Buy Score</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#10b981' }}>
                {thresholds.moderateBuyScore}
              </span>
            </div>
            <input
              type="range"
              min={30}
              max={65}
              value={thresholds.moderateBuyScore}
              onChange={(e) => setThresholds({ ...thresholds, moderateBuyScore: parseInt(e.target.value) })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Combined score must be ≥ this value
            </div>
          </div>

          {/* Moderate Buy Confidence */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Moderate Buy Confidence</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#10b981' }}>
                {Math.round(thresholds.moderateBuyConfidence * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={75}
              value={thresholds.moderateBuyConfidence * 100}
              onChange={(e) => setThresholds({ ...thresholds, moderateBuyConfidence: parseInt(e.target.value) / 100 })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Overall confidence must be ≥ this value
            </div>
          </div>
        </div>

        {/* SELL Thresholds */}
        <div>
          <div style={{ fontSize: '16px', fontWeight: '600', color: '#ef4444', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🔴</span>
            <span>SELL Signal Thresholds</span>
          </div>

          {/* Strong Sell Score */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Strong Sell Score</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#ef4444' }}>
                {thresholds.strongSellScore}
              </span>
            </div>
            <input
              type="range"
              min={-80}
              max={-50}
              value={thresholds.strongSellScore}
              onChange={(e) => setThresholds({ ...thresholds, strongSellScore: parseInt(e.target.value) })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Combined score must be ≤ this value
            </div>
          </div>

          {/* Strong Sell Confidence */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Strong Sell Confidence</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#ef4444' }}>
                {Math.round(thresholds.strongSellConfidence * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={60}
              max={90}
              value={thresholds.strongSellConfidence * 100}
              onChange={(e) => setThresholds({ ...thresholds, strongSellConfidence: parseInt(e.target.value) / 100 })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Overall confidence must be ≥ this value
            </div>
          </div>

          {/* Moderate Sell Score */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Moderate Sell Score</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#ef4444' }}>
                {thresholds.moderateSellScore}
              </span>
            </div>
            <input
              type="range"
              min={-65}
              max={-30}
              value={thresholds.moderateSellScore}
              onChange={(e) => setThresholds({ ...thresholds, moderateSellScore: parseInt(e.target.value) })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Combined score must be ≤ this value
            </div>
          </div>

          {/* Moderate Sell Confidence */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: '600' }}>Moderate Sell Confidence</span>
              <span style={{ fontSize: '15px', fontWeight: '700', color: '#ef4444' }}>
                {Math.round(thresholds.moderateSellConfidence * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={75}
              value={thresholds.moderateSellConfidence * 100}
              onChange={(e) => setThresholds({ ...thresholds, moderateSellConfidence: parseInt(e.target.value) / 100 })}
              style={{
                width: '100%',
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(51, 65, 85, 0.5)',
                outline: 'none',
                WebkitAppearance: 'none',
                cursor: 'pointer'
              }}
            />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Overall confidence must be ≥ this value
            </div>
          </div>
        </div>
      </div>
    </div>
  );

// Risk Management Tab


}
