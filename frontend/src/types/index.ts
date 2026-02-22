// Core types based on MVP specification

export interface Ticker {
  id: number;
  symbol: string;
  name: string;
  market: 'BET' | 'NYSE' | 'NASDAQ';
  industry?: string;
  sector?: string;
  currency?: string;
  market_cap?: number;
  priority: 'high' | 'medium' | 'low';
  is_active: boolean;
  primary_language: string;
  
  // ✅ Keyword management (NEW - from backend)
  relevance_keywords: string[];
  sentiment_keywords_positive: string[];
  sentiment_keywords_negative: string[];
  news_sources_preferred: string[];
  news_sources_blocked: string[];
  
  created_at: string;
  updated_at: string;
}

// ✅ NEW: Ticker creation type
export interface TickerCreate {
  symbol: string;
  name?: string;
  market?: string;
  industry?: string;
  sector?: string;
  currency?: string;
  priority?: 'high' | 'medium' | 'low';
  is_active?: boolean;
  primary_language?: string;
  relevance_keywords?: string[];
  sentiment_keywords_positive?: string[];
  sentiment_keywords_negative?: string[];
  news_sources_preferred?: string[];
  news_sources_blocked?: string[];
}

// ✅ NEW: Ticker update type (all fields optional)
export interface TickerUpdate {
  name?: string;
  market?: string;
  industry?: string;
  sector?: string;
  currency?: string;
  priority?: 'high' | 'medium' | 'low';
  is_active?: boolean;
  primary_language?: string;
  relevance_keywords?: string[];
  sentiment_keywords_positive?: string[];
  sentiment_keywords_negative?: string[];
  news_sources_preferred?: string[];
  news_sources_blocked?: string[];
}

export interface NewsSource {
  id: number;
  name: string;
  type: 'api' | 'rss' | 'scraper';
  url?: string;
  credibility_weight: number;
  is_enabled: boolean;
  polling_frequency_hours: number;
}

export interface NewsItem {
  id: number;
  url: string;
  source: {
    name: string;
    credibility: number;
  };
  title: string;
  description?: string;
  published_at: string;
  fetched_at: string;
  sentiment: {
    score: number; // -1.0 to +1.0
    confidence: number; // 0.0 to 1.0
    label: 'positive' | 'neutral' | 'negative';
  };
  relevance_score: number;
  categories: string[];
  is_duplicate: boolean;
  duplicate_count?: number;
}

export interface SentimentSnapshot {
  ticker_id: number;
  ticker_symbol: string;
  weighted_avg: number;
  confidence: number;
  news_count: number;
  time_distribution: {
    '0-2h': { avg: number; count: number };
    '2-4h': { avg: number; count: number };
    '4-8h': { avg: number; count: number };
    '8-12h': { avg: number; count: number };
  };
  calculated_at: string;
}

export interface TechnicalIndicators {
  ticker_symbol: string;
  score: number;
  confidence: number;
  components: {
    trend: number;
    momentum: number;
    volatility: number;
    volume: number;
  };
  indicators: {
    sma_20?: number;
    sma_50?: number;
    sma_200?: number;
    rsi?: number;
    macd?: number;
    adx?: number;
  };
  support_resistance: {
    nearest_support: number;
    nearest_resistance: number;
    current_price: number;
  };
  calculated_at: string;
}

export interface Signal {
  id: number;
  ticker_symbol: string;
  decision: 'BUY' | 'SELL' | 'HOLD';
  strength: 'STRONG' | 'MODERATE' | 'WEAK';
  combined_score: number;
  overall_confidence: number;
  
  sentiment_score: number;
  technical_score: number;
  risk_score: number;
  
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward_ratio: number;
  
  reasoning: {
    sentiment: {
      summary: string;
      key_news: string[];
      score: number;
    };
    technical: {
      summary: string;
      key_signals: string[];
      score: number;
    };
    risk?: {
      summary: string;
      factors: string[];
    };
  };
  
  created_at: string;
  expires_at: string;
  status: 'active' | 'expired' | 'archived';
  simulated_trade?: {
    id: number;
    status: 'OPEN' | 'CLOSED';
    direction: 'LONG' | 'SHORT';
    pnl_percent: number | null;
    pnl_amount_huf: number | null;
    exit_reason: string | null;
    entry_price: number;
    exit_price: number | null;
    position_size_shares: number | null;
    usd_huf_rate: number | null;
  } | null;
}

export interface SentimentConfig {
  decay_0_2h: number;
  decay_2_4h: number;
  decay_4_8h: number;
  decay_8_12h: number;
  credibility_weight: number;
  relevance_weight: number;
  use_market_cap_weighting: boolean;
  use_industry_context: boolean;
}

export interface SignalConfig {
  sentiment_weight: number;
  technical_weight: number;
  risk_weight: number;
  strong_buy_score: number;
  strong_buy_confidence: number;
  moderate_buy_score: number;
  moderate_buy_confidence: number;
  strong_sell_score: number;
  strong_sell_confidence: number;
  moderate_sell_score: number;
  moderate_sell_confidence: number;
  active_signal_ttl_hours: number;
  archive_after_hours: number;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// Filter types
export interface SignalFilters {
  decision?: ('BUY' | 'SELL' | 'HOLD')[];
  strength?: ('STRONG' | 'MODERATE' | 'WEAK')[];
  market?: ('BET' | 'NYSE' | 'NASDAQ')[];
  status?: 'active' | 'expired' | 'archived';
}

// ✅ Re-export types for convenience
export type SignalsResponse = { signals: Signal[]; total: number };
export type NewsResponse = { news: NewsItem[]; total: number };
export type TechnicalData = TechnicalIndicators;

// ====================================================================
// TRACKBACK SYSTEM TYPES
// ====================================================================

// Signal History filters
export interface SignalHistoryFilters {
  ticker_symbols?: string[];
  from_date?: string; // ISO 8601 format: YYYY-MM-DD
  to_date?: string;   // ISO 8601 format: YYYY-MM-DD
  decisions?: ('BUY' | 'SELL' | 'HOLD')[];
  strengths?: ('STRONG' | 'MODERATE' | 'WEAK')[];
  min_score?: number;
  max_score?: number;
  exit_reasons?: ('SL' | 'TP' | 'REV' | 'EOD' | 'OPEN' | 'NONE')[];
  limit?: number;
  offset?: number;
}

// Simulated Trade types
export interface SimulatedTrade {
  id: number;
  signal_id: number;
  ticker_symbol: string;
  
  // Entry data
  entry_signal_decision: 'BUY' | 'SELL';
  entry_signal_strength: 'STRONG' | 'MODERATE' | 'WEAK';
  entry_price: number;
  entry_timestamp: string;
  
  // Position sizing
  position_size_shares: number;
  position_value: number;
  
  // Exit data
  exit_price: number;
  exit_timestamp: string;
  exit_reason: 'take_profit' | 'stop_loss' | 'trailing_stop' | 'time_based' | 'signal_reversal';
  
  // P&L calculation
  gross_pnl: number;
  gross_pnl_percent: number;
  
  // K&H brokerage fees
  entry_fee: number;
  exit_fee: number;
  total_fees: number;
  
  // Net result
  net_pnl: number;
  net_pnl_percent: number;
  
  // Metadata
  holding_period_hours: number;
  risk_reward_ratio: number;
  created_at: string;
}

// Trade Exit record (for tracking multiple exit attempts)
export interface TradeExit {
  id: number;
  simulated_trade_id: number;
  exit_type: 'take_profit' | 'stop_loss' | 'trailing_stop';
  exit_price: number;
  exit_timestamp: string;
  was_triggered: boolean;
  created_at: string;
}

// Performance Analytics types
export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  
  total_gross_pnl: number;
  total_net_pnl: number;
  total_fees: number;
  
  avg_win: number;
  avg_loss: number;
  largest_win: number;
  largest_loss: number;
  
  avg_holding_period_hours: number;
  
  profit_factor: number; // sum(wins) / abs(sum(losses))
  sharpe_ratio?: number;
}

export interface PerformanceByTicker {
  ticker_symbol: string;
  metrics: PerformanceMetrics;
}

export interface PerformanceByStrategy {
  decision: 'BUY' | 'SELL';
  strength: 'STRONG' | 'MODERATE' | 'WEAK';
  metrics: PerformanceMetrics;
}

// API response types for trackback
export interface SignalHistoryPnlSummary {
  closed_count: number;
  open_count: number;
  open_trade_ids: number[];
  total_pnl_huf: number | null;
  total_pnl_percent: number | null;
}

export interface SignalHistoryResponse {
  signals: Signal[];
  total: number;
  pnl_summary: SignalHistoryPnlSummary;
  filters_applied: SignalHistoryFilters;
}

export interface SimulatedTradesResponse {
  trades: SimulatedTrade[];
  total: number;
  summary: {
    total_pnl: number;
    win_rate: number;
    avg_holding_hours: number;
  };
}
