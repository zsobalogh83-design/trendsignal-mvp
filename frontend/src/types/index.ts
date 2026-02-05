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
