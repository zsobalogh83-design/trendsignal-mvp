import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSignals } from '../hooks/useApi';
import { FiRefreshCw, FiStar } from 'react-icons/fi';
import { useQueryClient } from '@tanstack/react-query';

export function Dashboard() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<'active' | 'expired' | 'archived'>('active');
  const [activeFilter, setActiveFilter] = useState('all');
  const [isGenerating, setIsGenerating] = useState(false);
  
  const { data, isLoading, error, refetch } = useSignals({ status: statusFilter, limit: 50 });

  const signals = data?.signals || [];

  // ===== FILTER SIGNALS BASED ON ACTIVE FILTER =====
  const filteredSignals = signals.filter((signal: any) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'buy') return signal.decision === 'BUY';
    if (activeFilter === 'sell') return signal.decision === 'SELL';
    if (activeFilter === 'strong') return signal.strength === 'STRONG';
    return true;
  });

  // ===== REFRESH SIGNALS - Generate + Invalidate Cache =====
  const handleRefreshSignals = async () => {
    setIsGenerating(true);
    
    try {
      console.log('🎯 Triggering signal generation...');
      
      // Step 1: Generate new signals on backend
      const generateResponse = await fetch('http://localhost:8000/api/v1/signals/generate', {
        method: 'POST'
      });
      
      if (!generateResponse.ok) {
        throw new Error('Failed to generate signals');
      }
      
      const result = await generateResponse.json();
      console.log('✅ Signals generated:', result);
      
      // Step 2: INVALIDATE cache to force fresh fetch
      await queryClient.invalidateQueries({ queryKey: ['signals'] });
      
      // Step 3: Refetch the updated signals list
      await refetch();
      
      console.log('✅ Dashboard refreshed with fresh data');
      
    } catch (error) {
      console.error('❌ Error refreshing signals:', error);
      alert('Failed to refresh signals. Check console.');
    } finally {
      setIsGenerating(false);
    }
  };

  const getDecisionBadgeClass = (decision: string, strength: string) => {
    if (decision === 'BUY') {
      return strength === 'STRONG' 
        ? 'bg-green-500/20 text-green-400 border-green-500/30'
        : 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
    if (decision === 'SELL') {
      return strength === 'STRONG'
        ? 'bg-red-500/20 text-red-400 border-red-500/30'
        : 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    }
    return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  };

  const getDecisionIcon = (decision: string) => {
    if (decision === 'BUY') return '🟢';
    if (decision === 'SELL') return '🔴';
    return '⚪';
  };

  const scoreToPercentage = (score: number) => {
    return ((score + 100) / 2);
  };

  if (error) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)', padding: '32px' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '20px', color: '#ef4444' }}>
            Error loading signals: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)',
      color: '#e0e7ff',
      padding: '20px'
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          paddingBottom: '40px',
          borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
          marginBottom: '30px'
        }}>
          <div style={{
            fontSize: '28px',
            fontWeight: '700',
            background: 'linear-gradient(135deg, #3b82f6 0%, #10b981 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            📈 TrendSignal
          </div>
          
          <div style={{ display: 'flex', gap: '30px' }}>
            <Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '14px', fontWeight: '600' }}>
              Dashboard
            </Link>
            <Link to="/history" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
              📊 History
            </Link>
            <Link to="/news" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
              📰 News
            </Link>
            <Link to="/optimizer" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
              🧬 Optimizer
            </Link>
            <Link to="/settings" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
              ⚙️ Settings
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '15px', marginBottom: '25px', flexWrap: 'wrap' }}>
          {['all', 'buy', 'sell', 'strong'].map(filter => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              style={{
                background: activeFilter === filter ? 'rgba(59, 130, 246, 0.2)' : 'rgba(51, 65, 85, 0.5)',
                border: `1px solid ${activeFilter === filter ? '#3b82f6' : 'rgba(99, 102, 241, 0.3)'}`,
                color: activeFilter === filter ? '#60a5fa' : '#cbd5e1',
                padding: '10px 20px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                transition: 'all 0.3s'
              }}
            >
              {filter === 'all' && 'All Signals'}
              {filter === 'buy' && '🟢 Buy Only'}
              {filter === 'sell' && '🔴 Sell Only'}
              {filter === 'strong' && 'Strong Only'}
            </button>
          ))}
          
          <button
            onClick={handleRefreshSignals}
            disabled={isLoading || isGenerating}
            style={{
              marginLeft: 'auto',
              background: isGenerating 
                ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              border: 'none',
              color: 'white',
              padding: '10px 20px',
              borderRadius: '8px',
              cursor: (isLoading || isGenerating) ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: (isLoading || isGenerating) ? 0.5 : 1
            }}
          >
            <FiRefreshCw style={{ animation: (isLoading || isGenerating) ? 'spin 1s linear infinite' : 'none' }} />
            {isGenerating ? 'Generating...' : isLoading ? 'Loading...' : 'Refresh Signals'}
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div style={{ textAlign: 'center', paddingTop: '60px' }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              border: '4px solid rgba(59, 130, 246, 0.2)', 
              borderTop: '4px solid #3b82f6',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }}></div>
            <p style={{ color: '#64748b', marginTop: '20px' }}>Loading signals...</p>
          </div>
        )}

        {/* Signal Cards - COMPACT LAYOUT */}
        {!isLoading && filteredSignals.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: '16px'
          }}>
            {filteredSignals.map((signal: any) => (
              <div
                key={signal.id}
                style={{
                  background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  borderRadius: '12px',
                  padding: '16px',
                  transition: 'all 0.3s',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(59, 130, 246, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Header - COMPACT */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '4px' }}>
                      {signal.ticker_symbol}
                    </div>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '3px 10px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: '600',
                      background: signal.decision === 'BUY' ? 'rgba(16, 185, 129, 0.2)' : signal.decision === 'SELL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                      color: signal.decision === 'BUY' ? '#10b981' : signal.decision === 'SELL' ? '#ef4444' : '#94a3b8',
                      border: `1px solid ${signal.decision === 'BUY' ? 'rgba(16, 185, 129, 0.3)' : signal.decision === 'SELL' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(148, 163, 184, 0.3)'}`
                    }}>
                      {getDecisionIcon(signal.decision)} {signal.strength} {signal.decision}
                    </span>
                  </div>
                  <button style={{
                    background: 'rgba(251, 191, 36, 0.1)',
                    border: '1px solid rgba(251, 191, 36, 0.3)',
                    borderRadius: '6px',
                    padding: '4px',
                    cursor: 'pointer',
                    color: '#fbbf24',
                    fontSize: '14px'
                  }}>
                    <FiStar size={14} />
                  </button>
                </div>

                {/* Score Section - COMPACT */}
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '12px', color: '#64748b' }}>Score</span>
                    <span style={{
                      fontSize: '20px',
                      fontWeight: '700',
                      color: signal.combined_score > 0 ? '#10b981' : signal.combined_score < 0 ? '#ef4444' : '#94a3b8'
                    }}>
                      {signal.combined_score > 0 ? '+' : ''}{signal.combined_score.toFixed(1)}
                    </span>
                  </div>
                  
                  <div style={{ 
                    width: '100%', 
                    height: '6px', 
                    background: 'rgba(51, 65, 85, 0.5)', 
                    borderRadius: '3px',
                    overflow: 'hidden',
                    marginBottom: '6px'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${scoreToPercentage(signal.combined_score)}%`,
                      background: signal.combined_score > 0 
                        ? 'linear-gradient(90deg, #10b981 0%, #059669 100%)'
                        : signal.combined_score < 0
                        ? 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)'
                        : '#94a3b8',
                      transition: 'width 0.5s ease'
                    }}></div>
                  </div>

                  <div style={{ fontSize: '11px', color: '#64748b', textAlign: 'right' }}>
                    Confidence: {(signal.overall_confidence * 100).toFixed(0)}%
                  </div>
                </div>

                {/* Breakdown - COMPACT */}
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    📊 Breakdown
                  </div>
                  
                  {[
                    { label: 'Sentiment', value: signal.sentiment_score },
                    { label: 'Technical', value: signal.technical_score },
                    { label: 'Risk', value: signal.risk_score }
                  ].map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>{item.label}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: '600', color: '#e0e7ff', fontSize: '12px' }}>
                          {item.value > 0 ? '+' : ''}{item.value.toFixed(1)}
                        </span>
                        <div style={{ width: '60px', height: '3px', background: 'rgba(51, 65, 85, 0.5)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{
                            height: '100%',
                            width: `${scoreToPercentage(item.value)}%`,
                            background: 'linear-gradient(90deg, #10b981 0%, #3b82f6 100%)',
                            borderRadius: '2px'
                          }}></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Levels - COMPACT */}
                <div style={{
                  background: 'rgba(15, 23, 42, 0.5)',
                  borderRadius: '8px',
                  padding: '12px',
                  marginBottom: '12px'
                }}>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px', fontWeight: '600' }}>
                    💰 Entry & Exit
                  </div>
                  
                  {signal.decision !== 'HOLD' && signal.entry_price > 0 ? (
                    [
                      { label: 'Entry', value: signal.entry_price },
                      { label: 'Target', value: signal.take_profit, change: signal.take_profit && signal.entry_price ? ((signal.take_profit - signal.entry_price) / signal.entry_price * 100) : null, positive: true },
                      { label: 'Stop', value: signal.stop_loss, change: signal.stop_loss && signal.entry_price ? ((signal.stop_loss - signal.entry_price) / signal.entry_price * 100) : null, positive: false },
                      { label: 'R:R', value: signal.risk_reward_ratio, isRatio: true }
                    ].map((level, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>{level.label}</span>
                        <span style={{ 
                          fontWeight: '600', 
                          fontSize: '11px',
                          color: level.positive === true ? '#10b981' : level.positive === false ? '#ef4444' : '#e0e7ff' 
                        }}>
                          {level.isRatio 
                            ? (level.value ? `1:${level.value.toFixed(1)}` : '-')
                            : (level.value && !isNaN(level.value) ? `${level.value.toFixed(2)}` : '-')
                          }
                          {level.change && !isNaN(level.change) && ` (${level.change > 0 ? '+' : ''}${level.change.toFixed(1)}%)`}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '11px', color: '#64748b', fontStyle: 'italic', textAlign: 'center', padding: '8px' }}>
                      No position
                    </div>
                  )}
                </div>

                {/* Footer - COMPACT */}
                <div style={{
                  display: 'flex',
                  gap: '8px',
                  paddingTop: '12px',
                  borderTop: '1px solid rgba(51, 65, 85, 0.5)'
                }}>
                  <Link
                    to={`/signal/${signal.id}`}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      fontSize: '12px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                      color: 'white',
                      transition: 'all 0.3s',
                      textDecoration: 'none',
                      textAlign: 'center',
                      display: 'block'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 5px 20px rgba(59, 130, 246, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    Details
                  </Link>
                  <button style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    background: 'rgba(51, 65, 85, 0.5)',
                    color: '#cbd5e1',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    transition: 'all 0.3s'
                  }}>
                    Alert
                  </button>
                </div>

                {/* Timestamp - COMPACT */}
                <div style={{
                  fontSize: '11px',
                  color: '#64748b',
                  marginTop: '8px',
                  textAlign: 'center'
                }}>
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11px',
                    color: '#10b981',
                    fontWeight: '600'
                  }}>
                    <span style={{
                      width: '8px',
                      height: '8px',
                      background: '#10b981',
                      borderRadius: '50%',
                      animation: 'pulse 2s infinite'
                    }}></span>
                    LIVE
                  </span>
                  {' · Generated now · Expires in 24h'}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && signals.length > 0 && filteredSignals.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: '60px' }}>
            <div style={{ fontSize: '60px', marginBottom: '16px' }}>🔍</div>
            <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#cbd5e1', marginBottom: '8px' }}>
              No signals match your filter
            </h3>
            <p style={{ color: '#64748b' }}>
              Try selecting a different filter or click "All Signals"
            </p>
          </div>
        )}

        {/* No Signals At All */}
        {!isLoading && signals.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: '60px' }}>
            <div style={{ fontSize: '60px', marginBottom: '16px' }}>📊</div>
            <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#cbd5e1', marginBottom: '8px' }}>
              No signals found
            </h3>
            <p style={{ color: '#64748b' }}>
              Click "Refresh Signals" to generate new trading signals
            </p>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
