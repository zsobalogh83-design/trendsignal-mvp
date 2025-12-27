import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSignal } from '../hooks/useApi';
import { FiArrowLeft, FiBell, FiDownload } from 'react-icons/fi';

export function SignalDetail() {
  const { tickerId } = useParams<{ tickerId: string }>();
  const id = parseInt(tickerId || '1');
  
  const { data: signal, isLoading, error } = useSignal(id);
  
  const [openSections, setOpenSections] = useState<string[]>(['overview', 'levels']);

  const toggleSection = (section: string) => {
    setOpenSections(prev => 
      prev.includes(section) 
        ? prev.filter(s => s !== section)
        : [...prev, section]
    );
  };

  const scoreToPercentage = (score: number) => ((score + 100) / 2);

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '48px', height: '48px', border: '4px solid rgba(59, 130, 246, 0.2)', borderTop: '4px solid #3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
      </div>
    );
  }

  if (error || !signal) {
    return (
      <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)', padding: '32px' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '20px', color: '#ef4444' }}>
            Error loading signal details
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)', color: '#e0e7ff' }}>
      {/* Sticky Header */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'linear-gradient(135deg, rgba(10, 14, 39, 0.98) 0%, rgba(26, 31, 58, 0.98) 100%)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
        padding: '16px 20px'
      }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
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

          <div style={{ flex: 1, textAlign: 'center' }}>
            <span style={{
              fontSize: '20px',
              fontWeight: '700',
              background: 'linear-gradient(135deg, #3b82f6 0%, #10b981 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {signal.ticker_symbol}
            </span>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              background: 'rgba(16, 185, 129, 0.2)',
              color: '#10b981',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              marginLeft: '12px'
            }}>
              🟢 {signal.strength} {signal.decision}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              background: 'rgba(51, 65, 85, 0.5)',
              color: '#cbd5e1',
              transition: 'all 0.3s'
            }}>
              <FiBell style={{ marginRight: '6px' }} />
            </button>
            <button style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              color: 'white',
              transition: 'all 0.3s'
            }}>
              <FiDownload style={{ marginRight: '6px', display: 'inline' }} />
              Export
            </button>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 20px 40px 20px' }}>
        {/* Quick Nav */}
        <div style={{
          position: 'sticky',
          top: '73px',
          zIndex: 90,
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: '12px',
          padding: '12px 20px',
          marginBottom: '24px',
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
          alignItems: 'center',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
        }}>
          <span style={{ fontSize: '13px', color: '#64748b', fontWeight: '600' }}>Jump to:</span>
          {['Overview', 'Sentiment', 'Technical', 'Risk'].map(section => (
            <button
              key={section}
              onClick={() => toggleSection(section.toLowerCase())}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                color: '#cbd5e1',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px',
                transition: 'all 0.3s'
              }}
            >
              {section}
            </button>
          ))}
        </div>

        {/* Stats Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          {[
            { label: 'Combined Score', value: `${signal.combined_score > 0 ? '+' : ''}${signal.combined_score.toFixed(1)}`, sub: 'Strong bullish' },
            { label: 'Confidence', value: `${(signal.overall_confidence * 100).toFixed(0)}%`, sub: 'High reliability' },
            { label: 'Risk/Reward', value: `1:${signal.risk_reward_ratio.toFixed(1)}`, sub: 'Favorable' },
            { label: 'Entry Price', value: `${signal.entry_price.toFixed(2)}`, sub: signal.ticker_symbol.includes('.') ? 'HUF' : 'USD' }
          ].map((stat, idx) => (
            <div key={idx} style={{
              background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              borderRadius: '12px',
              padding: '20px',
              transition: 'all 0.3s'
            }}>
              <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                {stat.label}
              </div>
              <div style={{
                fontSize: '28px',
                fontWeight: '700',
                background: 'linear-gradient(135deg, #10b981 0%, #3b82f6 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                marginBottom: '6px'
              }}>
                {stat.value}
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                {stat.sub}
              </div>
            </div>
          ))}
        </div>

        {/* Score Breakdown */}
        <CollapsibleSection
          id="overview"
          icon="📊"
          title="Score Breakdown"
          badge={`${signal.combined_score.toFixed(1)}`}
          summary={`Sentiment: ${signal.sentiment_score.toFixed(1)} · Technical: ${signal.technical_score.toFixed(1)} · Risk: ${signal.risk_score.toFixed(1)}`}
          isOpen={openSections.includes('overview')}
          onToggle={() => toggleSection('overview')}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', margin: '20px 0' }}>
            {[
              { label: 'Sentiment', score: signal.sentiment_score, weight: 70, color: '#10b981', contribution: signal.sentiment_score * 0.7 },
              { label: 'Technical', score: signal.technical_score, weight: 20, color: '#3b82f6', contribution: signal.technical_score * 0.2 },
              { label: 'Risk', score: signal.risk_score, weight: 10, color: '#f59e0b', contribution: signal.risk_score * 0.1 }
            ].map((item, idx) => (
              <div key={idx} style={{
                background: 'rgba(15, 23, 42, 0.5)',
                borderRadius: '10px',
                padding: '16px',
                borderLeft: `4px solid ${item.color}`
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>{item.label}</div>
                <div style={{
                  fontSize: '32px',
                  fontWeight: '700',
                  background: 'linear-gradient(135deg, #10b981 0%, #3b82f6 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  marginBottom: '6px'
                }}>
                  {item.score > 0 ? '+' : ''}{item.score.toFixed(1)}
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8' }}>Weight: {item.weight}%</div>
                <div style={{ fontSize: '14px', color: '#10b981', fontWeight: '600', marginTop: '8px' }}>
                  Contributes: {item.contribution > 0 ? '+' : ''}{item.contribution.toFixed(1)}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* Levels */}
        <CollapsibleSection
          id="levels"
          icon="💰"
          title="Entry & Exit Levels"
          badge="Recommended"
          isOpen={openSections.includes('levels')}
          onToggle={() => toggleSection('levels')}
        >
          <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: '12px', padding: '20px', margin: '20px 0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              {[
                { type: '🎯 Take-Profit', price: signal.take_profit, change: ((signal.take_profit - signal.entry_price) / signal.entry_price * 100), style: 'take-profit', color: '#10b981' },
                { type: '📍 Entry Price', price: signal.entry_price, change: 0, style: 'entry', color: '#3b82f6' },
                { type: '🛡️ Stop-Loss', price: signal.stop_loss, change: ((signal.stop_loss - signal.entry_price) / signal.entry_price * 100), style: 'stop-loss', color: '#ef4444' }
              ].map((level, idx) => (
                <div key={idx} style={{
                  textAlign: 'center',
                  padding: '16px',
                  borderRadius: '8px',
                  background: 'rgba(30, 41, 59, 0.5)',
                  border: `2px solid ${level.color}33`
                }}>
                  <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px', textTransform: 'uppercase' }}>
                    {level.type}
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: '700', marginBottom: '4px', color: level.color }}>
                    {level.price.toFixed(2)} {signal.ticker_symbol.includes('.') ? 'HUF' : 'USD'}
                  </div>
                  <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                    {level.change !== 0 && `${level.change > 0 ? '+' : ''}${level.change.toFixed(1)}%`}
                    {level.change === 0 && 'Current Price'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CollapsibleSection>

        {/* Sentiment */}
        <CollapsibleSection
          id="sentiment"
          icon="📰"
          title="Sentiment Analysis"
          badge={`${signal.sentiment_score.toFixed(1)} · ${(signal.overall_confidence * 100).toFixed(0)}% conf`}
          summary={signal.reasoning.sentiment.summary}
          isOpen={openSections.includes('sentiment')}
          onToggle={() => toggleSection('sentiment')}
        >
          <div style={{ margin: '20px 0' }}>
            <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>Key News</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {signal.reasoning.sentiment.key_news.map((news: string, idx: number) => (
                <div key={idx} style={{
                  background: 'rgba(15, 23, 42, 0.5)',
                  borderRadius: '10px',
                  padding: '16px',
                  borderLeft: '4px solid #10b981'
                }}>
                  <div style={{ fontSize: '14px', fontWeight: '600', color: '#f1f5f9', marginBottom: '6px' }}>
                    🟢 {news}
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Recent · High credibility
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CollapsibleSection>

        {/* Technical */}
        <CollapsibleSection
          id="technical"
          icon="📈"
          title="Technical Analysis"
          badge={`${signal.technical_score.toFixed(1)}`}
          summary={signal.reasoning.technical.summary}
          isOpen={openSections.includes('technical')}
          onToggle={() => toggleSection('technical')}
        >
          <div style={{ margin: '20px 0' }}>
            <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>Key Signals</h4>
            <ul style={{ listStyle: 'none' }}>
              {signal.reasoning.technical.key_signals && signal.reasoning.technical.key_signals.map((sig: string, idx: number) => (
                <li key={idx} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 0',
                  borderBottom: idx < signal.reasoning.technical.key_signals.length - 1 ? '1px solid rgba(51, 65, 85, 0.3)' : 'none'
                }}>
                  <span style={{ fontSize: '16px', marginTop: '2px' }}>✅</span>
                  <span style={{ flex: 1, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>{sig}</span>
                </li>
              ))}
            </ul>
          </div>
        </CollapsibleSection>

        {/* Risk */}
        {signal.reasoning.risk && (
          <CollapsibleSection
            id="risk"
            icon="🛡️"
            title="Risk Assessment"
            badge={`${signal.risk_score.toFixed(1)}`}
            summary={signal.reasoning.risk.summary}
            isOpen={openSections.includes('risk')}
            onToggle={() => toggleSection('risk')}
          >
            <div style={{ margin: '20px 0' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                {signal.reasoning.risk.factors.map((factor: string, idx: number) => (
                  <div key={idx} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(15, 23, 42, 0.5)',
                    padding: '10px 14px',
                    borderRadius: '8px'
                  }}>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>{factor}</span>
                  </div>
                ))}
              </div>
            </div>
          </CollapsibleSection>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// Collapsible Section Component
function CollapsibleSection({ 
  id, 
  icon, 
  title, 
  badge, 
  summary, 
  isOpen, 
  onToggle, 
  children 
}: any) {
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
      border: '1px solid rgba(99, 102, 241, 0.3)',
      borderRadius: '12px',
      marginBottom: '16px',
      overflow: 'hidden',
      transition: 'all 0.3s'
    }}>
      <div
        onClick={onToggle}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 24px',
          cursor: 'pointer',
          userSelect: 'none',
          background: isOpen ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
          borderBottom: isOpen ? '1px solid rgba(99, 102, 241, 0.2)' : 'none',
          transition: 'all 0.3s'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>{icon}</span>
          <div>
            <span style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9' }}>{title}</span>
            {badge && (
              <span style={{
                background: 'rgba(59, 130, 246, 0.2)',
                color: '#60a5fa',
                padding: '4px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: '600',
                marginLeft: '12px'
              }}>
                {badge}
              </span>
            )}
            {summary && (
              <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '8px' }}>
                {summary}
              </div>
            )}
          </div>
        </div>
        <span style={{
          fontSize: '20px',
          color: '#64748b',
          transition: 'transform 0.3s',
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)'
        }}>
          ▼
        </span>
      </div>
      {isOpen && (
        <div style={{ padding: '0 24px 24px 24px' }}>
          {children}
        </div>
      )}
    </div>
  );
}
