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

  const jumpToSection = (section: string) => {
    const sectionId = section.toLowerCase();
    
    // Open section if closed
    if (!openSections.includes(sectionId)) {
      setOpenSections(prev => [...prev, sectionId]);
    }
    
    // Scroll to section after a small delay (to let it open first)
    setTimeout(() => {
      const element = document.getElementById(`section-${sectionId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
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
              onClick={() => jumpToSection(section)}
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
              { 
                label: 'Sentiment', 
                score: signal.sentiment_score, 
                weight: signal.reasoning.components?.sentiment?.weight ? Math.round(signal.reasoning.components.sentiment.weight * 100) : null,
                contribution: signal.reasoning.components?.sentiment?.contribution || (signal.sentiment_score * 0.7),
                color: '#10b981' 
              },
              { 
                label: 'Technical', 
                score: signal.technical_score, 
                weight: signal.reasoning.components?.technical?.weight ? Math.round(signal.reasoning.components.technical.weight * 100) : null,
                contribution: signal.reasoning.components?.technical?.contribution || (signal.technical_score * 0.2),
                color: '#3b82f6' 
              },
              { 
                label: 'Risk', 
                score: signal.risk_score, 
                weight: signal.reasoning.components?.risk?.weight ? Math.round(signal.reasoning.components.risk.weight * 100) : null,
                contribution: signal.reasoning.components?.risk?.contribution || (signal.risk_score * 0.1),
                color: '#f59e0b' 
              }
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
                {item.weight !== null && (
                  <div style={{ fontSize: '13px', color: '#94a3b8' }}>Weight: {item.weight}%</div>
                )}
                <div style={{ fontSize: '14px', color: '#10b981', fontWeight: '600', marginTop: '8px' }}>
                  Contributes: {item.contribution > 0 ? '+' : ''}{item.contribution.toFixed(1)}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* Levels */}
        {(() => {
          const rr = signal.risk_reward_ratio;
          const rrGood = rr >= 1.5;
          const rrWarn = rr >= 0.8 && rr < 1.5;
          const rrBad  = rr < 0.8;
          const rrColor  = rrGood ? '#10b981' : rrWarn ? '#f59e0b' : '#ef4444';
          const rrBg     = rrGood ? 'rgba(16,185,129,0.12)' : rrWarn ? 'rgba(245,158,11,0.12)' : 'rgba(239,68,68,0.12)';
          const rrBorder = rrGood ? 'rgba(16,185,129,0.35)' : rrWarn ? 'rgba(245,158,11,0.35)' : 'rgba(239,68,68,0.35)';
          const rrIcon   = rrGood ? '✅' : rrWarn ? '⚠️' : '🚨';
          const rrLabel  = rrGood ? 'Jó R:R arány' : rrWarn ? 'Gyenge R:R arány' : 'Rossz R:R arány';
          const rrSub    = rrGood ? 'Kedvező kockázat/hozam' : rrWarn ? 'Minimális szint alatt' : 'ATR override aktív';

          const currency = signal.ticker_symbol.includes('.') ? 'HUF' : 'USD';

          return (
            <CollapsibleSection
              id="levels"
              icon="💰"
              title="Entry & Exit Levels"
              badge={`R:R 1:${rr.toFixed(2)}`}
              isOpen={openSections.includes('levels')}
              onToggle={() => toggleSection('levels')}
            >
              {/* R:R Quality Banner */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                background: rrBg,
                border: `1px solid ${rrBorder}`,
                borderRadius: '10px',
                padding: '12px 16px',
                margin: '16px 0 8px 0'
              }}>
                <span style={{ fontSize: '20px' }}>{rrIcon}</span>
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: '700', color: rrColor, fontSize: '14px' }}>{rrLabel}</span>
                  <span style={{ color: '#64748b', fontSize: '13px', marginLeft: '10px' }}>{rrSub}</span>
                </div>
                <div style={{
                  background: rrBg,
                  border: `1px solid ${rrBorder}`,
                  borderRadius: '6px',
                  padding: '4px 10px',
                  fontWeight: '700',
                  fontSize: '15px',
                  color: rrColor,
                  fontFamily: 'monospace'
                }}>
                  1:{rr.toFixed(2)}
                </div>
              </div>

              {/* SL/TP method badges */}
              {(() => {
                const meta = signal.reasoning?.levels_meta;
                if (!meta) return null;

                const methodLabel: Record<string, string> = {
                  sr: 'S/R alapú',
                  atr: 'ATR alapú',
                  atr_conf: 'ATR (conf-adj)',
                  blended: 'S/R + ATR blend',
                  tightened: 'Tightened (R:R)',
                  atr_override: 'ATR override',
                };
                const methodColor: Record<string, string> = {
                  sr: '#10b981',
                  atr: '#60a5fa',
                  atr_conf: '#818cf8',
                  blended: '#f59e0b',
                  tightened: '#fb923c',
                  atr_override: '#ef4444',
                };

                const slColor = methodColor[meta.sl_method] || '#94a3b8';
                const tpColor = methodColor[meta.tp_method] || '#94a3b8';

                return (
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '12px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(30,41,59,0.6)', borderRadius: '6px', padding: '5px 10px', border: `1px solid ${slColor}44` }}>
                      <span style={{ fontSize: '11px', color: '#64748b' }}>🛡️ SL módszer:</span>
                      <span style={{ fontSize: '12px', fontWeight: '700', color: slColor }}>{methodLabel[meta.sl_method] || meta.sl_method}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(30,41,59,0.6)', borderRadius: '6px', padding: '5px 10px', border: `1px solid ${tpColor}44` }}>
                      <span style={{ fontSize: '11px', color: '#64748b' }}>🎯 TP módszer:</span>
                      <span style={{ fontSize: '12px', fontWeight: '700', color: tpColor }}>{methodLabel[meta.tp_method] || meta.tp_method}</span>
                    </div>
                  </div>
                );
              })()}

              <div style={{ background: 'rgba(15, 23, 42, 0.5)', borderRadius: '12px', padding: '20px', margin: '12px 0 20px 0' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                  {[
                    { type: '🎯 Take-Profit', price: signal.take_profit, change: ((signal.take_profit - signal.entry_price) / signal.entry_price * 100), color: '#10b981' },
                    { type: '📍 Entry Price', price: signal.entry_price, change: 0, color: '#3b82f6' },
                    { type: '🛡️ Stop-Loss',   price: signal.stop_loss,   change: ((signal.stop_loss - signal.entry_price) / signal.entry_price * 100), color: '#ef4444' }
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
                        {level.price.toFixed(2)} {currency}
                      </div>
                      <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                        {level.change !== 0 ? `${level.change > 0 ? '+' : ''}${level.change.toFixed(1)}%` : 'Current Price'}
                      </div>
                    </div>
                  ))}
                </div>

                {/* R:R visual bar */}
                {(() => {
                  const risk   = Math.abs((signal.stop_loss - signal.entry_price) / signal.entry_price * 100);
                  const reward = Math.abs((signal.take_profit - signal.entry_price) / signal.entry_price * 100);
                  const total  = risk + reward;
                  const riskPct   = (risk / total * 100).toFixed(1);
                  const rewardPct = (reward / total * 100).toFixed(1);
                  return (
                    <div style={{ marginTop: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>
                        <span>🛡️ Kockázat {risk.toFixed(1)}%</span>
                        <span>🎯 Hozam {reward.toFixed(1)}%</span>
                      </div>
                      <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: 'rgba(30,41,59,0.8)' }}>
                        <div style={{ width: `${riskPct}%`, background: 'linear-gradient(90deg, #ef4444, #f87171)', transition: 'width 0.4s' }} />
                        <div style={{ width: `${rewardPct}%`, background: 'linear-gradient(90deg, #34d399, #10b981)', transition: 'width 0.4s' }} />
                      </div>
                    </div>
                  );
                })()}
              </div>
            </CollapsibleSection>
          );
        })()}

        {/* Sentiment */}
        <CollapsibleSection
          id="sentiment"
          icon="📰"
          title="Sentiment Analysis"
          badge={`${signal.sentiment_score.toFixed(1)} · ${(signal.sentiment_confidence * 100).toFixed(0)}% conf`}
          summary={signal.reasoning?.sentiment?.summary}
          isOpen={openSections.includes('sentiment')}
          onToggle={() => toggleSection('sentiment')}
        >
          <div style={{ margin: '20px 0' }}>
            <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>Key News</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {(signal.reasoning?.sentiment?.key_news || []).map((news: any, idx: number) => {
                // Handle both old format (string) and new format (object with url)
                const newsTitle = typeof news === 'string' ? news : news.title;
                const newsUrl = typeof news === 'object' ? news.url : null;
                
                return (
                  <div key={idx} style={{
                    background: 'rgba(15, 23, 42, 0.5)',
                    borderRadius: '10px',
                    padding: '16px',
                    borderLeft: '4px solid #10b981',
                    cursor: newsUrl ? 'pointer' : 'default',
                    transition: 'all 0.3s'
                  }}
                  onClick={() => newsUrl && window.open(newsUrl, '_blank')}
                  onMouseEnter={(e) => {
                    if (newsUrl) {
                      e.currentTarget.style.background = 'rgba(16, 185, 129, 0.1)';
                      e.currentTarget.style.transform = 'translateX(4px)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(15, 23, 42, 0.5)';
                    e.currentTarget.style.transform = 'translateX(0)';
                  }}
                  >
                    <div style={{ fontSize: '14px', fontWeight: '600', color: '#f1f5f9', marginBottom: '6px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span>🟢</span>
                      <span style={{ flex: 1 }}>{newsTitle}</span>
                      {newsUrl && (
                        <span style={{ fontSize: '12px', color: '#60a5fa', opacity: 0.7 }}>
                          🔗
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginLeft: '24px' }}>
                      Recent · High credibility {newsUrl && '· Click to open'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </CollapsibleSection>

        {/* Technical */}
        <CollapsibleSection
          id="technical"
          icon="📈"
          title="Technical Analysis"
          badge={`${signal.technical_score.toFixed(1)} · ${(signal.technical_confidence * 100).toFixed(0)}% conf`}
          summary={signal.reasoning?.technical?.summary}
          isOpen={openSections.includes('technical')}
          onToggle={() => toggleSection('technical')}
        >
          <div style={{ margin: '20px 0' }}>
            <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>Key Signals</h4>
            <ul style={{ listStyle: 'none' }}>
              {(signal.reasoning?.technical?.key_signals || []).map((sig: string, idx: number) => (
                <li key={idx} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '10px 0',
                  borderBottom: idx < (signal.reasoning?.technical?.key_signals?.length || 0) - 1 ? '1px solid rgba(51, 65, 85, 0.3)' : 'none'
                }}>
                  <span style={{ fontSize: '16px', marginTop: '2px' }}>✅</span>
                  <span style={{ flex: 1, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>{sig}</span>
                </li>
              ))}
            </ul>
            
            {/* Indicator Table */}
            {(signal.reasoning.components?.technical || signal.reasoning?.technical) && (
              <div style={{ marginTop: '24px' }}>
                <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>📊 Indicators</h4>
                <div style={{ 
                  background: 'rgba(15, 23, 42, 0.5)', 
                  borderRadius: '8px', 
                  overflow: 'hidden',
                  border: '1px solid rgba(51, 65, 85, 0.5)'
                }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'rgba(30, 41, 59, 0.5)' }}>
                        <th style={{ padding: '12px', textAlign: 'left', fontSize: '12px', color: '#64748b', fontWeight: '600' }}>Indicator</th>
                        <th style={{ padding: '12px', textAlign: 'right', fontSize: '12px', color: '#64748b', fontWeight: '600' }}>Value</th>
                        <th style={{ padding: '12px', textAlign: 'right', fontSize: '12px', color: '#64748b', fontWeight: '600' }}>Signal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {signal.reasoning.components?.technical?.sma_20 && (
                        <tr style={{ borderTop: '1px solid rgba(51, 65, 85, 0.3)' }}>
                          <td style={{ padding: '12px', fontSize: '13px', color: '#cbd5e1' }}>SMA 20</td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '13px', color: '#f1f5f9', fontWeight: '600' }}>
                            ${signal.reasoning.components.technical.sma_20.toFixed(2)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '12px' }}>
                            <span style={{ 
                              padding: '4px 8px', 
                              borderRadius: '4px',
                              background: signal.entry_price > signal.reasoning.components.technical.sma_20 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                              color: signal.entry_price > signal.reasoning.components.technical.sma_20 ? '#10b981' : '#ef4444'
                            }}>
                              {signal.entry_price > signal.reasoning.components.technical.sma_20 ? 'Bullish' : 'Bearish'}
                            </span>
                          </td>
                        </tr>
                      )}
                      {signal.reasoning.components?.technical?.sma_50 && (
                        <tr style={{ borderTop: '1px solid rgba(51, 65, 85, 0.3)' }}>
                          <td style={{ padding: '12px', fontSize: '13px', color: '#cbd5e1' }}>SMA 50</td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '13px', color: '#f1f5f9', fontWeight: '600' }}>
                            ${signal.reasoning.components.technical.sma_50.toFixed(2)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '12px' }}>
                            <span style={{ 
                              padding: '4px 8px', 
                              borderRadius: '4px',
                              background: signal.entry_price > signal.reasoning.components.technical.sma_50 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                              color: signal.entry_price > signal.reasoning.components.technical.sma_50 ? '#10b981' : '#ef4444'
                            }}>
                              {signal.entry_price > signal.reasoning.components.technical.sma_50 ? 'Bullish' : 'Bearish'}
                            </span>
                          </td>
                        </tr>
                      )}
                      {signal.reasoning.components?.technical?.rsi && (
                        <tr style={{ borderTop: '1px solid rgba(51, 65, 85, 0.3)' }}>
                          <td style={{ padding: '12px', fontSize: '13px', color: '#cbd5e1' }}>RSI (14)</td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '13px', color: '#f1f5f9', fontWeight: '600' }}>
                            {signal.reasoning.components.technical.rsi.toFixed(1)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '12px' }}>
                            <span style={{ 
                              padding: '4px 8px', 
                              borderRadius: '4px',
                              background: signal.reasoning.components.technical.rsi > 70 ? 'rgba(239, 68, 68, 0.2)' : 
                                         signal.reasoning.components.technical.rsi > 55 ? 'rgba(16, 185, 129, 0.2)' :
                                         signal.reasoning.components.technical.rsi < 30 ? 'rgba(239, 68, 68, 0.2)' :
                                         signal.reasoning.components.technical.rsi < 45 ? 'rgba(251, 191, 36, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                              color: signal.reasoning.components.technical.rsi > 70 ? '#ef4444' : 
                                    signal.reasoning.components.technical.rsi > 55 ? '#10b981' :
                                    signal.reasoning.components.technical.rsi < 30 ? '#ef4444' :
                                    signal.reasoning.components.technical.rsi < 45 ? '#fbbf24' : '#94a3b8'
                            }}>
                              {signal.reasoning.components.technical.rsi > 70 ? 'Overbought' : 
                               signal.reasoning.components.technical.rsi > 55 ? 'Bullish' :
                               signal.reasoning.components.technical.rsi < 30 ? 'Oversold' :
                               signal.reasoning.components.technical.rsi < 45 ? 'Moderate' : 'Neutral'}
                            </span>
                          </td>
                        </tr>
                      )}
                      {signal.reasoning.components?.technical?.adx && (
                        <tr style={{ borderTop: '1px solid rgba(51, 65, 85, 0.3)' }}>
                          <td style={{ padding: '12px', fontSize: '13px', color: '#cbd5e1' }}>ADX (Trend)</td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '13px', color: '#f1f5f9', fontWeight: '600' }}>
                            {signal.reasoning.components.technical.adx.toFixed(1)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontSize: '12px' }}>
                            <span style={{ 
                              padding: '4px 8px', 
                              borderRadius: '4px',
                              background: signal.reasoning.components.technical.adx > 25 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                              color: signal.reasoning.components.technical.adx > 25 ? '#10b981' : '#94a3b8'
                            }}>
                              {signal.reasoning.components.technical.adx > 25 ? 'Strong' : 'Weak'}
                            </span>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {/* Price vs SMA Chart */}
            {(signal.reasoning.components?.technical?.sma_20 || signal.reasoning.components?.technical?.sma_50) && (
              <div style={{ marginTop: '24px' }}>
                <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>📍 Price vs Moving Averages</h4>
                <div style={{ 
                  background: 'rgba(15, 23, 42, 0.5)', 
                  borderRadius: '8px',
                  padding: '20px',
                  border: '1px solid rgba(51, 65, 85, 0.5)'
                }}>
                  {signal.reasoning.components?.technical?.sma_50 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', color: '#94a3b8' }}>SMA 50</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '14px', fontWeight: '600', color: '#f1f5f9' }}>
                            ${signal.reasoning.components.technical.sma_50.toFixed(2)}
                          </span>
                          <span style={{ fontSize: '12px', color: signal.entry_price > signal.reasoning.components.technical.sma_50 ? '#10b981' : '#ef4444' }}>
                            {signal.entry_price > signal.reasoning.components.technical.sma_50 ? '↑' : '↓'} 
                            {Math.abs(((signal.entry_price - signal.reasoning.components.technical.sma_50) / signal.reasoning.components.technical.sma_50) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <div style={{ 
                        height: '4px', 
                        background: 'rgba(51, 65, 85, 0.5)', 
                        borderRadius: '2px',
                        position: 'relative'
                      }}>
                        <div style={{
                          position: 'absolute',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          background: '#3b82f6',
                          top: '-2px'
                        }}></div>
                      </div>
                    </div>
                  )}
                  
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    padding: '12px',
                    background: 'rgba(59, 130, 246, 0.1)',
                    borderRadius: '6px',
                    marginBottom: signal.reasoning.components?.technical?.sma_20 ? '16px' : '0'
                  }}>
                    <span style={{ fontSize: '16px', fontWeight: '700', color: '#60a5fa' }}>
                      Current: ${signal.entry_price?.toFixed(2) || 'N/A'}
                    </span>
                  </div>
                  
                  {signal.reasoning.components?.technical?.sma_20 && (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', color: '#94a3b8' }}>SMA 20</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '14px', fontWeight: '600', color: '#f1f5f9' }}>
                            ${signal.reasoning.components.technical.sma_20.toFixed(2)}
                          </span>
                          <span style={{ fontSize: '12px', color: signal.entry_price > signal.reasoning.components.technical.sma_20 ? '#10b981' : '#ef4444' }}>
                            {signal.entry_price > signal.reasoning.components.technical.sma_20 ? '↑' : '↓'} 
                            {Math.abs(((signal.entry_price - signal.reasoning.components.technical.sma_20) / signal.reasoning.components.technical.sma_20) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      <div style={{ 
                        height: '4px', 
                        background: 'rgba(51, 65, 85, 0.5)', 
                        borderRadius: '2px',
                        position: 'relative'
                      }}>
                        <div style={{
                          position: 'absolute',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          background: '#10b981',
                          top: '-2px'
                        }}></div>
                      </div>
                    </div>
                  )}
                  
                  {(signal.reasoning.components?.technical?.sma_20 && signal.reasoning.components?.technical?.sma_50) && (
                    <div style={{ 
                      marginTop: '12px', 
                      padding: '10px', 
                      background: 'rgba(59, 130, 246, 0.1)',
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#60a5fa',
                      textAlign: 'center'
                    }}>
                      {signal.reasoning.components.technical.sma_20 > signal.reasoning.components.technical.sma_50 
                        ? '✨ Golden Cross (SMA20 > SMA50)' 
                        : '⚠️ Death Cross (SMA20 < SMA50)'}
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Volatility Gauge */}
            {signal.reasoning.components?.technical?.atr_pct && (
              <div style={{ marginTop: '24px' }}>
                <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>📉 Volatility</h4>
                <div style={{ 
                  background: 'rgba(15, 23, 42, 0.5)', 
                  borderRadius: '8px',
                  padding: '16px',
                  border: '1px solid rgba(51, 65, 85, 0.5)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontSize: '13px', color: '#94a3b8' }}>ATR (14-period)</span>
                    <span style={{ fontSize: '16px', fontWeight: '700', color: '#f1f5f9' }}>
                      {signal.reasoning.components.technical.atr_pct.toFixed(2)}%
                    </span>
                  </div>
                  <div style={{ 
                    height: '8px', 
                    background: 'rgba(51, 65, 85, 0.5)', 
                    borderRadius: '4px',
                    overflow: 'hidden',
                    position: 'relative'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min((signal.reasoning.components.technical.atr_pct / 5) * 100, 100)}%`,
                      background: signal.reasoning.components.technical.atr_pct < 2.0 ? 'linear-gradient(90deg, #10b981 0%, #059669 100%)' :
                                 signal.reasoning.components.technical.atr_pct < 4.0 ? 'linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%)' :
                                 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)',
                      borderRadius: '4px',
                      transition: 'width 0.5s ease-out'
                    }}></div>
                  </div>
                  <div style={{ 
                    marginTop: '8px', 
                    fontSize: '12px',
                    color: signal.reasoning.components.technical.atr_pct < 2.0 ? '#10b981' :
                           signal.reasoning.components.technical.atr_pct < 4.0 ? '#fbbf24' : '#ef4444',
                    fontWeight: '600'
                  }}>
                    {signal.reasoning.components.technical.atr_pct < 2.0 ? '🟢 Low Volatility' :
                     signal.reasoning.components.technical.atr_pct < 4.0 ? '🟡 Moderate Volatility' :
                     '🔴 High Volatility'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </CollapsibleSection>

        {/* Risk */}
        {signal.reasoning.risk && (
          <CollapsibleSection
            id="risk"
            icon="🛡️"
            title="Risk Assessment"
            badge={`${signal.risk_score.toFixed(1)} · ${(signal.reasoning.components?.risk?.confidence ? signal.reasoning.components.risk.confidence * 100 : 50).toFixed(0)}% conf`}
            summary={signal.reasoning?.risk?.summary}
            isOpen={openSections.includes('risk')}
            onToggle={() => toggleSection('risk')}
          >
            <div style={{ margin: '20px 0' }}>
              {/* Risk Factors (old style - keep for compatibility) */}
              {signal.reasoning?.risk?.factors && signal.reasoning.risk.factors.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>Risk Factors</h4>
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
              )}
              
              {/* Multi-Component Risk Breakdown */}
              {signal.reasoning.components?.risk?.components && (
                <div>
                  <h4 style={{ fontSize: '14px', color: '#64748b', marginBottom: '12px', fontWeight: '600' }}>🛡️ Risk Components</h4>
                  
                  {/* Volatility Component */}
                  {signal.reasoning.components.risk.components.volatility && (
                    <div style={{ 
                      background: 'rgba(15, 23, 42, 0.5)', 
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '12px',
                      borderLeft: `4px solid ${signal.reasoning.components.risk.components.volatility.risk > 0 ? '#10b981' : signal.reasoning.components.risk.components.volatility.risk < 0 ? '#ef4444' : '#94a3b8'}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', color: '#cbd5e1', fontWeight: '600' }}>
                          📉 Volatility (40% weight)
                        </span>
                        <span style={{ 
                          fontSize: '14px', 
                          fontWeight: '700',
                          color: signal.reasoning.components.risk.components.volatility.risk > 0 ? '#10b981' : signal.reasoning.components.risk.components.volatility.risk < 0 ? '#ef4444' : '#94a3b8'
                        }}>
                          {signal.reasoning.components.risk.components.volatility.risk > 0 ? '+' : ''}{signal.reasoning.components.risk.components.volatility.risk.toFixed(1)}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                        {signal.reasoning.components.risk.components.volatility.status}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        Confidence: {(signal.reasoning.components.risk.components.volatility.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  )}
                  
                  {/* Proximity Component */}
                  {signal.reasoning.components.risk.components.proximity && (
                    <div style={{ 
                      background: 'rgba(15, 23, 42, 0.5)', 
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '12px',
                      borderLeft: `4px solid ${signal.reasoning.components.risk.components.proximity.risk > 0 ? '#10b981' : signal.reasoning.components.risk.components.proximity.risk < 0 ? '#ef4444' : '#94a3b8'}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', color: '#cbd5e1', fontWeight: '600' }}>
                          📍 S/R Proximity (35% weight)
                        </span>
                        <span style={{ 
                          fontSize: '14px', 
                          fontWeight: '700',
                          color: signal.reasoning.components.risk.components.proximity.risk > 0 ? '#10b981' : signal.reasoning.components.risk.components.proximity.risk < 0 ? '#ef4444' : '#94a3b8'
                        }}>
                          {signal.reasoning.components.risk.components.proximity.risk > 0 ? '+' : ''}{signal.reasoning.components.risk.components.proximity.risk.toFixed(1)}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                        {signal.reasoning.components.risk.components.proximity.status}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        Confidence: {(signal.reasoning.components.risk.components.proximity.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  )}
                  
                  {/* Trend Strength Component */}
                  {signal.reasoning.components.risk.components.trend_strength && (
                    <div style={{ 
                      background: 'rgba(15, 23, 42, 0.5)', 
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '12px',
                      borderLeft: `4px solid ${signal.reasoning.components.risk.components.trend_strength.risk > 0 ? '#10b981' : signal.reasoning.components.risk.components.trend_strength.risk < 0 ? '#ef4444' : '#94a3b8'}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontSize: '13px', color: '#cbd5e1', fontWeight: '600' }}>
                          📊 Trend Strength (25% weight)
                        </span>
                        <span style={{ 
                          fontSize: '14px', 
                          fontWeight: '700',
                          color: signal.reasoning.components.risk.components.trend_strength.risk > 0 ? '#10b981' : signal.reasoning.components.risk.components.trend_strength.risk < 0 ? '#ef4444' : '#94a3b8'
                        }}>
                          {signal.reasoning.components.risk.components.trend_strength.risk > 0 ? '+' : ''}{signal.reasoning.components.risk.components.trend_strength.risk.toFixed(1)}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
                        {signal.reasoning.components.risk.components.trend_strength.status}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        Confidence: {(signal.reasoning.components.risk.components.trend_strength.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  )}
                  
                  {/* Overall Risk Summary */}
                  <div style={{
                    background: 'rgba(59, 130, 246, 0.1)',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    borderRadius: '8px',
                    padding: '14px',
                    marginTop: '16px'
                  }}>
                    <div style={{ fontSize: '12px', color: '#60a5fa' }}>
                      💡 Overall Risk Score: <strong>{signal.risk_score > 0 ? '+' : ''}{signal.risk_score.toFixed(1)}</strong> 
                      {' '}(Confidence: {(signal.reasoning.components.risk.confidence * 100).toFixed(0)}%)
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
                      Calculated from: Volatility (40%) + S/R Proximity (35%) + Trend Strength (25%)
                    </div>
                  </div>
                </div>
              )}
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
    <div 
      id={`section-${id}`}
      style={{
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '12px',
        marginBottom: '16px',
        overflow: 'hidden',
        transition: 'all 0.3s',
        scrollMarginTop: '100px'
      }}
    >
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
