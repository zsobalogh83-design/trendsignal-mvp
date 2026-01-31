import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiArrowLeft, FiSave, FiEdit2, FiTrash2, FiPlus } from 'react-icons/fi';

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
        {activeTab === 3 && <TechnicalTab />}
        {activeTab === 4 && <SignalsTab componentWeights={componentWeights} setComponentWeights={setComponentWeights} thresholds={thresholds} setThresholds={setThresholds} />}

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
function TechnicalTab() {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
      border: '1px solid rgba(99, 102, 241, 0.3)',
      borderRadius: '16px',
      padding: '24px'
    }}>
      <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
        📈 Technical Indicator Weights
      </div>
      <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>
        Customize the importance of different technical indicators
      </div>
      <div style={{ fontSize: '14px', color: '#cbd5e1', padding: '40px', textAlign: 'center' }}>
        Technical parameter configuration coming in Phase 2
      </div>
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
}
