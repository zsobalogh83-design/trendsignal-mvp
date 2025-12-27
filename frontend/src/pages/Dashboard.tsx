import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useSignals } from '../hooks/useApi';
import { FiRefreshCw, FiStar } from 'react-icons/fi';

export function Dashboard() {
  const [statusFilter, setStatusFilter] = useState<'active' | 'expired' | 'archived'>('active');
  const [activeFilter, setActiveFilter] = useState('all');
  
  const { data, isLoading, error, refetch } = useSignals({ status: statusFilter, limit: 50 });

  const signals = data?.signals || [];

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
            <Link to="/news" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
              📰 News
            </Link>
            <a href="#" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>
              ⚙️ Settings
            </a>
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
            onClick={() => refetch()}
            disabled={isLoading}
            style={{
              marginLeft: 'auto',
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              border: 'none',
              color: 'white',
              padding: '10px 20px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: isLoading ? 0.5 : 1
            }}
          >
            <FiRefreshCw style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
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

        {/* Signal Cards */}
        {!isLoading && signals.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
            gap: '25px',
            marginTop: '30px'
          }}>
            {signals.map((signal: any) => (
              <div
                key={signal.id}
                style={{
                  background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  borderRadius: '16px',
                  padding: '24px',
                  position: 'relative',
                  overflow: 'hidden',
                  transition: 'all 0.3s',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#3b82f6';
                  e.currentTarget.style.transform = 'translateY(-5px)';
                  e.currentTarget.style.boxShadow = '0 10px 40px rgba(59, 130, 246, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Card Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                  <div>
                    <div style={{ fontSize: '24px', fontWeight: '700', color: '#f1f5f9', marginBottom: '4px' }}>
                      {signal.ticker_symbol}
                    </div>
                    <div style={{ fontSize: '13px', color: '#64748b' }}>
                      {signal.ticker_symbol === 'AAPL' && 'Apple Inc.'}
                      {signal.ticker_symbol === 'MSFT' && 'Microsoft Corp.'}
                      {signal.ticker_symbol === 'GOOGL' && 'Alphabet Inc.'}
                    </div>
                  </div>
                  <button style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', opacity: 0.5 }}>
                    <FiStar />
                  </button>
                </div>

                {/* Decision Badge */}
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '600',
                  marginBottom: '20px',
                  border: '1px solid'
                }}
                className={getDecisionBadgeClass(signal.decision, signal.strength)}
                >
                  <span>{getDecisionIcon(signal.decision)}</span>
                  <span>{signal.strength} {signal.decision}</span>
                </div>

                {/* Score Section */}
                <div style={{ marginBottom: '25px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{
                      fontSize: '32px',
                      fontWeight: '700',
                      background: 'linear-gradient(135deg, #10b981 0%, #3b82f6 100%)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      backgroundClip: 'text'
                    }}>
                      {signal.combined_score > 0 ? '+' : ''}{signal.combined_score.toFixed(1)}
                    </div>
                    <div style={{
                      background: 'rgba(59, 130, 246, 0.2)',
                      color: '#60a5fa',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '13px',
                      fontWeight: '600'
                    }}>
                      {(signal.overall_confidence * 100).toFixed(0)}% confidence
                    </div>
                  </div>
                  <div style={{
                    height: '8px',
                    background: 'rgba(51, 65, 85, 0.5)',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${scoreToPercentage(signal.combined_score)}%`,
                      background: 'linear-gradient(90deg, #10b981 0%, #3b82f6 100%)',
                      borderRadius: '4px',
                      transition: 'width 1s ease-out'
                    }}></div>
                  </div>
                </div>

                {/* Breakdown */}
                <div style={{ marginBottom: '25px' }}>
                  <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    📊 Score Breakdown
                  </div>
                  
                  {[
                    { label: 'Sentiment (70%)', value: signal.sentiment_score },
                    { label: 'Technical (20%)', value: signal.technical_score },
                    { label: 'Risk (10%)', value: signal.risk_score }
                  ].map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <span style={{ fontSize: '13px', color: '#94a3b8' }}>{item.label}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontWeight: '600', color: '#e0e7ff' }}>
                          {item.value > 0 ? '+' : ''}{item.value.toFixed(1)}
                        </span>
                        <div style={{ width: '100px', height: '4px', background: 'rgba(51, 65, 85, 0.5)', borderRadius: '2px', overflow: 'hidden' }}>
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

                {/* Levels */}
                <div style={{
                  background: 'rgba(15, 23, 42, 0.5)',
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '20px'
                }}>
                  <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>
                    💰 Entry & Exit Levels
                  </div>
                  
                  {[
                    { label: 'Entry Price', value: signal.entry_price },
                    { label: 'Take-Profit', value: signal.take_profit, change: ((signal.take_profit - signal.entry_price) / signal.entry_price * 100), positive: true },
                    { label: 'Stop-Loss', value: signal.stop_loss, change: ((signal.stop_loss - signal.entry_price) / signal.entry_price * 100), positive: false },
                    { label: 'Risk/Reward', value: `1:${signal.risk_reward_ratio.toFixed(1)}`, isRatio: true }
                  ].map((level, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '13px', color: '#94a3b8' }}>{level.label}</span>
                      <span style={{ 
                        fontWeight: '600', 
                        color: level.positive === true ? '#10b981' : level.positive === false ? '#ef4444' : '#e0e7ff' 
                      }}>
                        {level.isRatio ? level.value : `${level.value.toFixed(2)} ${signal.ticker_symbol.includes('.') ? 'HUF' : 'USD'}`}
                        {level.change && ` (${level.change > 0 ? '+' : ''}${level.change.toFixed(1)}%)`}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Quick Info */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#94a3b8' }}>
                    <span>📰</span>
                    <span>Recent news</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#94a3b8' }}>
                    <span>📈</span>
                    <span>Analysis ready</span>
                  </div>
                </div>

                {/* Footer */}
                <div style={{
                  display: 'flex',
                  gap: '10px',
                  paddingTop: '16px',
                  borderTop: '1px solid rgba(51, 65, 85, 0.5)'
                }}>
                  <Link
                    to={`/signal/${signal.id}`}
                    style={{
                      flex: 1,
                      padding: '10px 16px',
                      borderRadius: '8px',
                      border: 'none',
                      fontSize: '13px',
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
                    View Details
                  </Link>
                  <button style={{
                    flex: 1,
                    padding: '10px 16px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    background: 'rgba(51, 65, 85, 0.5)',
                    color: '#cbd5e1',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    transition: 'all 0.3s'
                  }}>
                    Set Alert
                  </button>
                </div>

                {/* Timestamp */}
                <div style={{
                  fontSize: '12px',
                  color: '#64748b',
                  marginTop: '12px',
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
        {!isLoading && signals.length === 0 && (
          <div style={{ textAlign: 'center', paddingTop: '60px' }}>
            <div style={{ fontSize: '60px', marginBottom: '16px' }}>📊</div>
            <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#cbd5e1', marginBottom: '8px' }}>
              No signals found
            </h3>
            <p style={{ color: '#64748b' }}>
              Try adjusting your filters or wait for new signals to be generated.
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
