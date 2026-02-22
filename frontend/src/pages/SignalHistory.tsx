import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { FiFilter, FiX, FiCalendar, FiTrendingUp, FiTrendingDown, FiMinus, FiChevronDown, FiChevronRight, FiPlay } from 'react-icons/fi';
import { Signal, SignalHistoryFilters, SignalHistoryResponse, Ticker } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Map: trade_id → { current_price, unrealized_pnl_percent, unrealized_pnl_huf }
type OpenPnlMap = Record<number, { current_price: number | null; unrealized_pnl_percent: number | null; unrealized_pnl_huf: number | null }>;

type ExitReasonFilter = 'SL' | 'TP' | 'REV' | 'EOD' | 'OPEN' | 'NONE';

function getExitCategory(trade: Signal['simulated_trade']): ExitReasonFilter {
  if (!trade) return 'NONE';
  if (trade.status === 'OPEN') return 'OPEN';
  if (trade.exit_reason === 'SL_HIT') return 'SL';
  if (trade.exit_reason === 'TP_HIT') return 'TP';
  if (trade.exit_reason === 'OPPOSING_SIGNAL') return 'REV';
  if (trade.exit_reason === 'EOD_AUTO_LIQUIDATION') return 'EOD';
  return 'NONE';
}

export function SignalHistory() {
  const [filters, setFilters] = useState<SignalHistoryFilters>({
    from_date: getDefaultFromDate(),
    to_date: getDefaultToDate(),
    ticker_symbols: [],
    decisions: [],
    strengths: [],
    exit_reasons: [],
  });

  const [showFilters, setShowFilters] = useState(true);
  const [simulateStatus, setSimulateStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [simulateStats, setSimulateStats] = useState<Record<string, number> | null>(null);

  const queryClient = useQueryClient();

  const { data: tickersData } = useQuery({
    queryKey: ['tickers'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/tickers`);
      if (!response.ok) throw new Error('Failed to fetch tickers');
      const tickers = await response.json();
      return { tickers };
    },
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['signal-history', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.from_date) params.append('from_date', filters.from_date);
      if (filters.to_date) params.append('to_date', filters.to_date);
      if (filters.ticker_symbols && filters.ticker_symbols.length > 0) {
        filters.ticker_symbols.forEach(s => params.append('ticker_symbols', s));
      }
      if (filters.decisions && filters.decisions.length > 0) {
        filters.decisions.forEach(d => params.append('decisions', d));
      }
      if (filters.strengths && filters.strengths.length > 0) {
        filters.strengths.forEach(s => params.append('strengths', s));
      }
      if (filters.min_score !== undefined) params.append('min_score', String(filters.min_score));
      if (filters.exit_reasons && filters.exit_reasons.length > 0) {
        filters.exit_reasons.forEach(r => params.append('exit_reasons', r));
      }
      const response = await fetch(`${API_BASE}/signals/history?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch signal history');
      return response.json() as Promise<SignalHistoryResponse>;
    },
  });

  // Fetch unrealized P&L for all open trades
  const { data: openPnlData } = useQuery<OpenPnlMap>({
    queryKey: ['open-pnl'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/simulated-trades/open-pnl`);
      if (!response.ok) throw new Error('Failed to fetch open PnL');
      return response.json() as Promise<OpenPnlMap>;
    },
    refetchInterval: 60_000, // refresh every 60s
    staleTime: 30_000,
  });

  const handleResetFilters = () => {
    setFilters({
      from_date: getDefaultFromDate(),
      to_date: getDefaultToDate(),
      ticker_symbols: [],
      decisions: [],
      strengths: [],
      min_score: undefined,
      exit_reasons: [],
    });
  };

  const toggleExitReasonFilter = (reason: ExitReasonFilter) => {
    setFilters(prev => ({
      ...prev,
      exit_reasons: prev.exit_reasons?.includes(reason)
        ? prev.exit_reasons.filter(r => r !== reason)
        : [...(prev.exit_reasons || []), reason],
    }));
  };

  const toggleTickerFilter = (symbol: string) => {
    setFilters(prev => ({
      ...prev,
      ticker_symbols: prev.ticker_symbols?.includes(symbol)
        ? prev.ticker_symbols.filter(s => s !== symbol)
        : [...(prev.ticker_symbols || []), symbol],
    }));
  };

  const toggleDecisionFilter = (decision: 'BUY' | 'SELL' | 'HOLD') => {
    setFilters(prev => ({
      ...prev,
      decisions: prev.decisions?.includes(decision)
        ? prev.decisions.filter(d => d !== decision)
        : [...(prev.decisions || []), decision],
    }));
  };

  const toggleStrengthFilter = (strength: 'STRONG' | 'MODERATE' | 'WEAK') => {
    setFilters(prev => ({
      ...prev,
      strengths: prev.strengths?.includes(strength)
        ? prev.strengths.filter(s => s !== strength)
        : [...(prev.strengths || []), strength],
    }));
  };

  const handleSimulate = async () => {
    setSimulateStatus('running');
    setSimulateStats(null);
    try {
      const body: Record<string, unknown> = {};
      if (filters.from_date) body.date_from = filters.from_date;
      if (filters.to_date) body.date_to = filters.to_date;
      if (filters.ticker_symbols && filters.ticker_symbols.length > 0) {
        body.symbols = filters.ticker_symbols;
      }
      const response = await fetch(`${API_BASE}/simulated-trades/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error('Backtest failed');
      const result = await response.json();
      setSimulateStats(result.stats);
      setSimulateStatus('done');
      // Refresh signal history and open PnL
      queryClient.invalidateQueries({ queryKey: ['signal-history'] });
      queryClient.invalidateQueries({ queryKey: ['open-pnl'] });
    } catch (e) {
      setSimulateStatus('error');
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)',
      color: '#e0e7ff',
      padding: '15px'
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: '15px',
          borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
          marginBottom: '15px'
        }}>
          <div>
            <div style={{
              fontSize: '22px',
              fontWeight: '700',
              background: 'linear-gradient(135deg, #3b82f6 0%, #10b981 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              marginBottom: '4px'
            }}>
              📊 Signal History
            </div>
            <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>
              Browse and analyze past trading signals
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {/* Simulate button */}
            <button
              onClick={handleSimulate}
              disabled={simulateStatus === 'running'}
              style={{
                background: simulateStatus === 'running'
                  ? 'rgba(59, 130, 246, 0.2)'
                  : simulateStatus === 'done'
                  ? 'rgba(16, 185, 129, 0.2)'
                  : simulateStatus === 'error'
                  ? 'rgba(239, 68, 68, 0.2)'
                  : 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
                border: `1px solid ${simulateStatus === 'done' ? '#10b981' : simulateStatus === 'error' ? '#ef4444' : 'rgba(99, 102, 241, 0.5)'}`,
                color: simulateStatus === 'done' ? '#34d399' : simulateStatus === 'error' ? '#f87171' : '#e0e7ff',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: simulateStatus === 'running' ? 'not-allowed' : 'pointer',
                fontSize: '13px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
                opacity: simulateStatus === 'running' ? 0.7 : 1,
              }}
            >
              {simulateStatus === 'running' ? (
                <>
                  <span style={{
                    display: 'inline-block',
                    width: '12px',
                    height: '12px',
                    border: '2px solid rgba(255,255,255,0.3)',
                    borderTop: '2px solid white',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }} />
                  Simulating...
                </>
              ) : simulateStatus === 'done' ? (
                <>✓ Done</>
              ) : simulateStatus === 'error' ? (
                <>✗ Error</>
              ) : (
                <>
                  <FiPlay size={13} />
                  Simulate
                </>
              )}
            </button>

            <Link to="/" style={{
              background: 'rgba(51, 65, 85, 0.5)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              color: '#cbd5e1',
              padding: '10px 20px',
              borderRadius: '8px',
              textDecoration: 'none',
              fontSize: '14px',
              transition: 'all 0.3s'
            }}>
              ← Dashboard
            </Link>
          </div>
        </div>

        {/* Simulate result banner */}
        {simulateStatus === 'done' && simulateStats && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '10px',
            padding: '10px 16px',
            marginBottom: '15px',
            display: 'flex',
            gap: '24px',
            flexWrap: 'wrap',
            fontSize: '12px',
            color: '#94a3b8'
          }}>
            <span style={{ color: '#34d399', fontWeight: '600' }}>✓ Simulation complete</span>
            {Object.entries(simulateStats)
              .filter(([k]) => k !== 'errors')
              .map(([k, v]) => (
                <span key={k}>
                  <span style={{ color: '#cbd5e1' }}>{k.replace(/_/g, ' ')}:</span>{' '}
                  <span style={{ color: '#e0e7ff', fontWeight: '600' }}>{String(v)}</span>
                </span>
              ))}
          </div>
        )}

        {/* Filters */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.4)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          borderRadius: '12px',
          marginBottom: '15px',
          overflow: 'hidden'
        }}>
          <button
            onClick={() => setShowFilters(!showFilters)}
            style={{
              width: '100%',
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'transparent',
              border: 'none',
              color: '#e0e7ff',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FiFilter style={{ color: '#3b82f6', fontSize: '14px' }} />
              <span>Filters</span>
              {((filters.ticker_symbols?.length || 0) + (filters.decisions?.length || 0) + (filters.strengths?.length || 0) + (filters.exit_reasons?.length || 0) + (filters.min_score !== undefined ? 1 : 0)) > 0 && (
                <span style={{
                  background: 'rgba(59, 130, 246, 0.2)',
                  color: '#60a5fa',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  fontSize: '11px'
                }}>
                  {(filters.ticker_symbols?.length || 0) + (filters.decisions?.length || 0) + (filters.strengths?.length || 0) + (filters.exit_reasons?.length || 0) + (filters.min_score !== undefined ? 1 : 0)} active
                </span>
              )}
            </div>
            {showFilters ? <FiChevronDown size={16} /> : <FiChevronRight size={16} />}
          </button>

          {showFilters && (
            <div style={{
              padding: '12px 16px',
              borderTop: '1px solid rgba(99, 102, 241, 0.2)'
            }}>
              {/* Date Range */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                <div>
                  <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', marginBottom: '6px', fontWeight: '500' }}>
                    <FiCalendar style={{ display: 'inline', marginRight: '4px', fontSize: '12px' }} />
                    From Date
                  </label>
                  <input
                    type="date"
                    value={filters.from_date || ''}
                    onChange={(e) => setFilters(prev => ({ ...prev, from_date: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      background: 'rgba(30, 41, 59, 0.6)',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      borderRadius: '6px',
                      color: '#e0e7ff',
                      fontSize: '13px'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', marginBottom: '6px', fontWeight: '500' }}>
                    <FiCalendar style={{ display: 'inline', marginRight: '4px', fontSize: '12px' }} />
                    To Date
                  </label>
                  <input
                    type="date"
                    value={filters.to_date || ''}
                    onChange={(e) => setFilters(prev => ({ ...prev, to_date: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '6px 8px',
                      background: 'rgba(30, 41, 59, 0.6)',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      borderRadius: '6px',
                      color: '#e0e7ff',
                      fontSize: '13px'
                    }}
                  />
                </div>
              </div>

              {/* Tickers + Alert filter */}
              <div style={{ marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <label style={{ color: '#cbd5e1', fontSize: '12px', fontWeight: '500' }}>Tickers</label>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                  {tickersData?.tickers?.map((ticker) => (
                    <button
                      key={ticker.symbol}
                      onClick={() => toggleTickerFilter(ticker.symbol)}
                      style={{
                        background: filters.ticker_symbols?.includes(ticker.symbol) ? 'rgba(59, 130, 246, 0.2)' : 'rgba(51, 65, 85, 0.5)',
                        border: `1px solid ${filters.ticker_symbols?.includes(ticker.symbol) ? '#3b82f6' : 'rgba(99, 102, 241, 0.3)'}`,
                        color: filters.ticker_symbols?.includes(ticker.symbol) ? '#60a5fa' : '#cbd5e1',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: '500',
                        transition: 'all 0.2s'
                      }}
                    >
                      {ticker.symbol}
                    </button>
                  ))}
                  <div style={{ width: '1px', height: '20px', background: 'rgba(99, 102, 241, 0.3)', margin: '0 2px' }} />
                  <button
                    onClick={() => setFilters(prev => ({ ...prev, min_score: prev.min_score !== undefined ? undefined : 25 }))}
                    style={{
                      background: filters.min_score !== undefined ? 'rgba(245, 158, 11, 0.2)' : 'rgba(51, 65, 85, 0.5)',
                      border: `1px solid ${filters.min_score !== undefined ? '#f59e0b' : 'rgba(99, 102, 241, 0.3)'}`,
                      color: filters.min_score !== undefined ? '#fbbf24' : '#cbd5e1',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '12px',
                      fontWeight: '500',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      transition: 'all 0.2s'
                    }}
                    title="Csak kereskedési alertek (combined score ≥ 25)"
                  >
                    ⚡ Alert
                  </button>
                </div>
              </div>

              {/* Decision, Strength, Reset - ALL IN ONE ROW */}
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap' }}>
                {/* Decision */}
                <div style={{ flex: '1 1 auto' }}>
                  <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', marginBottom: '6px', fontWeight: '500' }}>Decision</label>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {(['BUY', 'SELL', 'HOLD'] as const).map((decision) => (
                      <button
                        key={decision}
                        onClick={() => toggleDecisionFilter(decision)}
                        style={{
                          background: filters.decisions?.includes(decision)
                            ? decision === 'BUY' ? 'rgba(16, 185, 129, 0.2)' : decision === 'SELL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(107, 114, 128, 0.2)'
                            : 'rgba(51, 65, 85, 0.5)',
                          border: `1px solid ${filters.decisions?.includes(decision)
                            ? decision === 'BUY' ? '#10b981' : decision === 'SELL' ? '#ef4444' : '#6b7280'
                            : 'rgba(99, 102, 241, 0.3)'}`,
                          color: filters.decisions?.includes(decision)
                            ? decision === 'BUY' ? '#34d399' : decision === 'SELL' ? '#f87171' : '#9ca3af'
                            : '#cbd5e1',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '12px',
                          fontWeight: '500',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          transition: 'all 0.2s'
                        }}
                      >
                        {decision === 'BUY' && <FiTrendingUp size={12} />}
                        {decision === 'SELL' && <FiTrendingDown size={12} />}
                        {decision === 'HOLD' && <FiMinus size={12} />}
                        {decision}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Strength */}
                <div style={{ flex: '1 1 auto' }}>
                  <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', marginBottom: '6px', fontWeight: '500' }}>Strength</label>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {(['STRONG', 'MODERATE', 'WEAK'] as const).map((strength) => (
                      <button
                        key={strength}
                        onClick={() => toggleStrengthFilter(strength)}
                        style={{
                          background: filters.strengths?.includes(strength) ? 'rgba(139, 92, 246, 0.2)' : 'rgba(51, 65, 85, 0.5)',
                          border: `1px solid ${filters.strengths?.includes(strength) ? '#8b5cf6' : 'rgba(99, 102, 241, 0.3)'}`,
                          color: filters.strengths?.includes(strength) ? '#a78bfa' : '#cbd5e1',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '12px',
                          fontWeight: '500',
                          transition: 'all 0.2s'
                        }}
                      >
                        {strength}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Exit / Trade státusz */}
                <div style={{ flex: '1 1 auto' }}>
                  <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', marginBottom: '6px', fontWeight: '500' }}>Exit / Státusz</label>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {([
                      { key: 'TP',   label: 'TP',   activeColor: '#34d399', activeBg: 'rgba(16, 185, 129, 0.2)',  activeBorder: '#10b981' },
                      { key: 'SL',   label: 'SL',   activeColor: '#f87171', activeBg: 'rgba(239, 68, 68, 0.2)',   activeBorder: '#ef4444' },
                      { key: 'REV',  label: 'REV',  activeColor: '#fb923c', activeBg: 'rgba(251, 146, 60, 0.2)',  activeBorder: '#f97316' },
                      { key: 'EOD',  label: 'EOD',  activeColor: '#94a3b8', activeBg: 'rgba(100, 116, 139, 0.2)', activeBorder: '#64748b' },
                      { key: 'OPEN', label: 'OPEN', activeColor: '#fbbf24', activeBg: 'rgba(251, 191, 36, 0.2)',  activeBorder: '#f59e0b' },
                      { key: 'NONE', label: '—',    activeColor: '#64748b', activeBg: 'rgba(51, 65, 85, 0.4)',    activeBorder: '#475569' },
                    ] as const).map(({ key, label, activeColor, activeBg, activeBorder }) => {
                      const active = (filters.exit_reasons || []).includes(key);
                      return (
                        <button
                          key={key}
                          onClick={() => toggleExitReasonFilter(key)}
                          style={{
                            background: active ? activeBg : 'rgba(51, 65, 85, 0.5)',
                            border: `1px solid ${active ? activeBorder : 'rgba(99, 102, 241, 0.3)'}`,
                            color: active ? activeColor : '#cbd5e1',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '12px',
                            fontWeight: '600',
                            transition: 'all 0.2s',
                            fontFamily: 'monospace',
                          }}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Reset */}
                <div style={{ flex: '0 0 auto' }}>
                  <button
                    onClick={handleResetFilters}
                    style={{
                      background: 'rgba(51, 65, 85, 0.5)',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      color: '#cbd5e1',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '12px',
                      fontWeight: '600',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all 0.2s',
                      height: '28px'
                    }}
                  >
                    <FiX size={14} />
                    Reset
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        <div style={{
          background: 'rgba(30, 41, 59, 0.4)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          borderRadius: '12px',
          overflow: 'hidden'
        }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(99, 102, 241, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 style={{ fontSize: '15px', fontWeight: '600', color: '#e0e7ff', margin: 0 }}>
              {isLoading ? 'Loading...' : `${data?.total || 0} signals found`}
            </h2>
            {!isLoading && data?.signals && data.signals.length > 0 && (() => {
              let closedCount: number;
              let openCount: number;
              let totalHuf: number;
              let totalPct: number | null;
              let hasAnyHuf: boolean;

              {
                const backendSummary = data.pnl_summary;
                closedCount = backendSummary?.closed_count ?? 0;
                openCount = backendSummary?.open_count ?? 0;
                totalHuf = backendSummary?.total_pnl_huf ?? 0;
                totalPct = backendSummary?.total_pnl_percent ?? null;
                hasAnyHuf = backendSummary?.total_pnl_huf !== null && backendSummary?.total_pnl_huf !== undefined;
                // Add unrealized PnL for open trades using the exact trade IDs from the backend summary
                if (openPnlData && backendSummary?.open_trade_ids?.length) {
                  for (const tradeId of backendSummary.open_trade_ids) {
                    const live = openPnlData[tradeId];
                    if (live?.unrealized_pnl_huf !== null && live?.unrealized_pnl_huf !== undefined) {
                      totalHuf += live.unrealized_pnl_huf;
                      hasAnyHuf = true;
                    }
                    if (live?.unrealized_pnl_percent !== null && live?.unrealized_pnl_percent !== undefined) {
                      totalPct = (totalPct ?? 0) + live.unrealized_pnl_percent;
                    }
                  }
                }
              }

              if (!hasAnyHuf && totalPct === null) return null;
              const isProfit = totalHuf >= 0;
              const hasOpen = openCount > 0;
              const color = isProfit ? '#34d399' : '#f87171';
              const borderColor = isProfit ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)';
              const bg = isProfit ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)';
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: bg, border: `1px solid ${borderColor}`, borderRadius: '8px', padding: '5px 12px' }}>
                  <span style={{ fontSize: '11px', color: '#64748b', fontWeight: '500' }}>
                    {closedCount} lezárt{hasOpen ? ` + ${openCount} nyitott` : ''}
                  </span>
                  {totalPct !== null && (
                    <span style={{ fontSize: '12px', fontWeight: '700', fontFamily: 'monospace', color }}>
                      {totalPct >= 0 ? '+' : ''}{totalPct.toFixed(2)}%
                      {hasOpen && <span style={{ color: '#64748b', fontSize: '10px', marginLeft: '2px' }}>~</span>}
                    </span>
                  )}
                  {hasAnyHuf && (
                    <span style={{ fontSize: '13px', fontWeight: '700', fontFamily: 'monospace', color, whiteSpace: 'nowrap' }}
                      title={hasOpen ? 'Tartalmaz nyitott (nem realizált) HUF összeget is' : undefined}>
                      {totalHuf >= 0 ? '+' : ''}{formatHuf(totalHuf)}
                      {hasOpen && <span style={{ color: '#64748b', fontSize: '10px', marginLeft: '2px' }}>~</span>}
                    </span>
                  )}
                </div>
              );
            })()}
          </div>

          {isLoading ? (
            <div style={{ padding: '60px', textAlign: 'center' }}>
              <div style={{
                display: 'inline-block',
                width: '48px',
                height: '48px',
                border: '4px solid rgba(59, 130, 246, 0.2)',
                borderTop: '4px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></div>
              <p style={{ color: '#64748b', marginTop: '20px' }}>Loading signals...</p>
            </div>
          ) : error ? (
            <div style={{ padding: '60px', textAlign: 'center' }}>
              <p style={{ color: '#ef4444' }}>Error loading signals</p>
              <button
                onClick={() => refetch()}
                style={{
                  marginTop: '16px',
                  background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                  border: 'none',
                  color: 'white',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600'
                }}
              >
                Retry
              </button>
            </div>
          ) : data?.signals && data.signals.length > 0 ? (() => {
            const visibleSignals = data.signals;
            return (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: '13px' }}>
                <thead style={{ background: 'rgba(15, 23, 42, 0.6)', borderBottom: '1px solid rgba(99, 102, 241, 0.2)' }}>
                  <tr>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Timestamp</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ticker</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Decision</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Strength</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Score</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Conf</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Entry</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Stop Loss</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Take Profit</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>R/R</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>P&L</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Nettó</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleSignals.map((signal, idx) => (
                    <tr
                      key={signal.id}
                      onClick={() => window.location.href = `/signal/${signal.id}`}
                      style={{
                        borderBottom: idx < data.signals.length - 1 ? '1px solid rgba(99, 102, 241, 0.1)' : 'none',
                        cursor: 'pointer',
                        transition: 'background-color 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.05)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '8px 12px', color: '#cbd5e1', fontSize: '12px' }}>{formatTimestamp(signal.created_at)}</td>
                      <td style={{ padding: '8px 12px', fontWeight: '600', color: '#e0e7ff' }}>{signal.ticker_symbol || '-'}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '3px',
                          padding: '3px 8px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: '600',
                          background: signal.decision === 'BUY' ? 'rgba(16, 185, 129, 0.15)' : signal.decision === 'SELL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(107, 114, 128, 0.15)',
                          color: signal.decision === 'BUY' ? '#34d399' : signal.decision === 'SELL' ? '#f87171' : '#9ca3af',
                          border: `1px solid ${signal.decision === 'BUY' ? 'rgba(16, 185, 129, 0.3)' : signal.decision === 'SELL' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(107, 114, 128, 0.3)'}`
                        }}>
                          {signal.decision === 'BUY' && <FiTrendingUp size={10} />}
                          {signal.decision === 'SELL' && <FiTrendingDown size={10} />}
                          {signal.decision === 'HOLD' && <FiMinus size={10} />}
                          {signal.decision}
                        </span>
                      </td>
                      <td style={{ padding: '8px 12px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '3px 8px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: '600',
                          background: signal.strength === 'STRONG' ? 'rgba(139, 92, 246, 0.15)' : signal.strength === 'MODERATE' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                          color: signal.strength === 'STRONG' ? '#a78bfa' : signal.strength === 'MODERATE' ? '#60a5fa' : '#94a3b8',
                          border: `1px solid ${signal.strength === 'STRONG' ? 'rgba(139, 92, 246, 0.3)' : signal.strength === 'MODERATE' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(100, 116, 139, 0.3)'}`
                        }}>
                          {signal.strength}
                        </span>
                      </td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '500', color: '#e0e7ff' }}>{signal.combined_score.toFixed(1)}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', color: '#cbd5e1', fontSize: '12px' }}>{(signal.overall_confidence * 100).toFixed(0)}%</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'monospace', color: '#e0e7ff', fontSize: '12px' }}>${signal.entry_price.toFixed(2)}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'monospace', color: '#f87171', fontSize: '12px' }}>${signal.stop_loss.toFixed(2)}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'monospace', color: '#34d399', fontSize: '12px' }}>${signal.take_profit.toFixed(2)}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '500', color: '#e0e7ff', fontSize: '12px' }}>{signal.risk_reward_ratio.toFixed(2)}</td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontSize: '12px', fontWeight: '600', fontFamily: 'monospace' }}>
                        {renderPnl(signal.simulated_trade, openPnlData)}
                      </td>
                      <td style={{ padding: '8px 12px', textAlign: 'right', fontSize: '12px', fontWeight: '600', fontFamily: 'monospace' }}>
                        {renderHuf(signal.simulated_trade, openPnlData)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            );
          })() : (
            <div style={{ padding: '60px', textAlign: 'center' }}>
              <p style={{ color: '#64748b' }}>No signals found matching your filters</p>
              <button
                onClick={handleResetFilters}
                style={{
                  marginTop: '16px',
                  background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                  border: 'none',
                  color: 'white',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600'
                }}
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function renderPnl(
  trade: Signal['simulated_trade'],
  openPnlMap: OpenPnlMap | undefined
): React.ReactNode {
  if (!trade) {
    return <span style={{ color: '#475569', fontSize: '11px' }}>—</span>;
  }

  if (trade.status === 'OPEN') {
    const live = openPnlMap?.[trade.id];
    const pnl = live?.unrealized_pnl_percent;

    const badge = (
      <span style={{
        display: 'inline-block',
        background: 'rgba(251, 191, 36, 0.15)',
        border: '1px solid rgba(251, 191, 36, 0.4)',
        color: '#fbbf24',
        fontSize: '9px',
        fontWeight: '700',
        letterSpacing: '0.04em',
        padding: '1px 4px',
        borderRadius: '4px',
        marginRight: '5px',
        verticalAlign: 'middle',
      }}>OPEN</span>
    );

    if (pnl === null || pnl === undefined) {
      return <span style={{ fontSize: '12px' }}>{badge}<span style={{ color: '#64748b' }}>—</span></span>;
    }

    const isProfit = pnl >= 0;
    const color = isProfit ? '#34d399' : '#f87171';
    const sign = isProfit ? '+' : '';

    return (
      <span style={{ fontSize: '12px' }} title="Unrealized P&L (live)">
        {badge}
        <span style={{ color, fontWeight: '600' }}>{sign}{pnl.toFixed(2)}%</span>
        <span style={{ color: '#64748b', fontSize: '10px', marginLeft: '2px' }}>~</span>
      </span>
    );
  }

  // CLOSED
  const pnl = trade.pnl_percent;

  const exitLabel = trade.exit_reason
    ? trade.exit_reason === 'SL_HIT' ? 'SL'
    : trade.exit_reason === 'TP_HIT' ? 'TP'
    : trade.exit_reason === 'OPPOSING_SIGNAL' ? 'REV'
    : trade.exit_reason === 'EOD_AUTO_LIQUIDATION' ? 'EOD'
    : 'CL'
    : 'CL';

  const badge = (
    <span style={{
      display: 'inline-block',
      background: 'rgba(100, 116, 139, 0.15)',
      border: '1px solid rgba(100, 116, 139, 0.35)',
      color: '#94a3b8',
      fontSize: '9px',
      fontWeight: '700',
      letterSpacing: '0.04em',
      padding: '1px 4px',
      borderRadius: '4px',
      marginRight: '5px',
      verticalAlign: 'middle',
    }} title={trade.exit_reason || 'CLOSED'}>{exitLabel}</span>
  );

  if (pnl === null || pnl === undefined) {
    return <span style={{ fontSize: '12px' }}>{badge}<span style={{ color: '#475569' }}>—</span></span>;
  }

  const isProfit = pnl >= 0;
  const color = isProfit ? '#34d399' : '#f87171';
  const sign = isProfit ? '+' : '';

  return (
    <span style={{ fontSize: '12px' }}>
      {badge}
      <span style={{ color, fontWeight: '600' }}>{sign}{pnl.toFixed(2)}%</span>
    </span>
  );
}

function renderHuf(
  trade: Signal['simulated_trade'],
  openPnlMap: OpenPnlMap | undefined
): React.ReactNode {
  if (!trade) return <span style={{ color: '#475569', fontSize: '11px' }}>—</span>;

  const fmt = (huf: number) => {
    const abs = Math.abs(huf);
    const sign = huf >= 0 ? '+' : '−';
    if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(2)}M`;
    if (abs >= 1_000) return `${sign}${Math.round(abs / 1_000)}k`;
    return `${sign}${Math.round(abs)}`;
  };

  if (trade.status === 'OPEN') {
    const live = openPnlMap?.[trade.id];
    const huf = live?.unrealized_pnl_huf;
    if (huf === null || huf === undefined) {
      return <span style={{ color: '#64748b', fontSize: '11px' }}>—</span>;
    }
    const color = huf >= 0 ? '#34d399' : '#f87171';
    return (
      <span style={{ color, fontSize: '12px' }} title="Unrealized HUF (live)">
        {fmt(huf)} Ft
        <span style={{ color: '#64748b', fontSize: '10px', marginLeft: '2px' }}>~</span>
      </span>
    );
  }

  // CLOSED
  const huf = trade.pnl_amount_huf;
  if (huf === null || huf === undefined) {
    return <span style={{ color: '#475569', fontSize: '11px' }}>—</span>;
  }
  const color = huf >= 0 ? '#34d399' : '#f87171';
  return <span style={{ color, fontSize: '12px' }}>{fmt(huf)} Ft</span>;
}

function formatHuf(value: number): string {
  return new Intl.NumberFormat('hu-HU', {
    style: 'currency',
    currency: 'HUF',
    maximumFractionDigits: 0,
  }).format(value);
}

interface SummaryResult {
  closedCount: number;
  openCount: number;
  totalHuf: number;
  totalPct: number | null;
  hasAnyHuf: boolean;
}

function calcSummary(signals: Signal[], openPnlMap: OpenPnlMap | undefined): SummaryResult {
  let totalHuf = 0;
  let totalPct = 0;
  let pctCount = 0;
  let closedCount = 0;
  let openCount = 0;
  let hasAnyHuf = false;

  for (const signal of signals) {
    const trade = signal.simulated_trade;
    if (!trade) continue;

    if (trade.status === 'CLOSED') {
      closedCount++;
      if (trade.pnl_amount_huf !== null && trade.pnl_amount_huf !== undefined) {
        totalHuf += trade.pnl_amount_huf;
        hasAnyHuf = true;
      }
      if (trade.pnl_percent !== null && trade.pnl_percent !== undefined) {
        totalPct += trade.pnl_percent;
        pctCount++;
      }
    } else if (trade.status === 'OPEN') {
      openCount++;
      const live = openPnlMap?.[trade.id];
      if (live?.unrealized_pnl_huf !== null && live?.unrealized_pnl_huf !== undefined) {
        totalHuf += live.unrealized_pnl_huf;
        hasAnyHuf = true;
      }
      if (live?.unrealized_pnl_percent !== null && live?.unrealized_pnl_percent !== undefined) {
        totalPct += live.unrealized_pnl_percent;
        pctCount++;
      }
    }
  }

  return {
    closedCount,
    openCount,
    totalHuf,
    totalPct: pctCount > 0 ? totalPct : null,
    hasAnyHuf,
  };
}

function getDefaultFromDate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 30);
  return date.toISOString().split('T')[0];
}

function getDefaultToDate(): string {
  const date = new Date();
  return date.toISOString().split('T')[0];
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
