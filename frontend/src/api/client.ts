import type {
  Ticker,
  TickerUpdate,
  NewsItem,
  SentimentSnapshot,
  TechnicalIndicators,
  Signal,
  NewsSource,
  SentimentConfig,
  SignalConfig,
  PaginatedResponse,
} from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || 'API request failed');
    }

    return response.json();
  }

  // ==========================================
  // TICKERS - Updated for new backend
  // ==========================================
  
  async getTickers(): Promise<Ticker[]> {
    // ✅ NEW: Backend returns array directly, not {tickers: [...]}
    return this.request('/tickers');
  }

  async getTicker(id: number): Promise<Ticker> {
    return this.request(`/tickers/${id}`);
  }

  async createTicker(ticker: Partial<Ticker>): Promise<Ticker> {
    return this.request('/tickers', {
      method: 'POST',
      body: JSON.stringify(ticker),
    });
  }

  async updateTicker(id: number, ticker: TickerUpdate): Promise<Ticker> {
    return this.request(`/tickers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(ticker),
    });
  }

  // ✅ NEW: Toggle active status
  async toggleTickerActive(id: number): Promise<Ticker> {
    return this.request(`/tickers/${id}/toggle`, {
      method: 'PATCH',
    });
  }

  async deleteTicker(id: number): Promise<void> {
    return this.request(`/tickers/${id}`, {
      method: 'DELETE',
    });
  }

  // ==========================================
  // NEWS
  // ==========================================
  
  async getNews(params: {
    ticker_symbol?: string;
    sentiment?: string;
    limit?: number;
  } = {}): Promise<{ news: any[]; total: number }> {
    const query = new URLSearchParams();
    if (params.ticker_symbol) query.append('ticker_symbol', params.ticker_symbol);
    if (params.sentiment) query.append('sentiment', params.sentiment);
    if (params.limit) query.append('limit', params.limit.toString());

    const queryString = query.toString();
    return this.request(`/news${queryString ? `?${queryString}` : ''}`);
  }

  async getNewsItem(id: number): Promise<NewsItem> {
    return this.request(`/news/${id}`);
  }

  async collectNews(): Promise<{ job_id: string }> {
    return this.request('/news/collect', { method: 'POST' });
  }

  // ==========================================
  // SENTIMENT
  // ==========================================
  
  async getSentiment(tickerId: number): Promise<SentimentSnapshot> {
    return this.request(`/sentiment/${tickerId}`);
  }

  async getSentimentHistory(
    tickerId: number,
    window: string = '24h'
  ): Promise<SentimentSnapshot[]> {
    return this.request(`/sentiment/${tickerId}/history?window=${window}`);
  }

  // ==========================================
  // TECHNICAL ANALYSIS
  // ==========================================
  
  async getTechnicalAnalysis(tickerId: number): Promise<TechnicalIndicators> {
    return this.request(`/technical/${tickerId}`);
  }

  async getTechnicalIndicators(tickerId: number): Promise<any> {
    return this.request(`/technical/${tickerId}/indicators`);
  }

  async getSupportResistance(tickerId: number): Promise<any> {
    return this.request(`/technical/${tickerId}/support-resistance`);
  }

  // ==========================================
  // SIGNALS
  // ==========================================
  
  async getSignals(params: {
    status?: 'active' | 'expired' | 'archived';
    limit?: number;
  } = {}): Promise<{ signals: Signal[]; total: number }> {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.limit) query.append('limit', params.limit.toString());

    return this.request(`/signals?${query}`);
  }

  async getSignal(tickerId: number): Promise<Signal> {
    return this.request(`/signals/${tickerId}`);
  }

  async generateSignals(): Promise<{ message: string }> {
    return this.request('/signals/generate', { method: 'POST' });
  }

  async generateSignal(tickerId: number): Promise<Signal> {
    return this.request(`/signals/generate/${tickerId}`, { method: 'POST' });
  }

  // ==========================================
  // CONFIGURATION
  // ==========================================
  
  async getSentimentConfig(): Promise<SentimentConfig> {
    return this.request('/config/sentiment');
  }

  async updateSentimentConfig(config: Partial<SentimentConfig>): Promise<SentimentConfig> {
    return this.request('/config/sentiment', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getSignalConfig(): Promise<SignalConfig> {
    return this.request('/config/signal');
  }

  async updateSignalConfig(config: Partial<SignalConfig>): Promise<SignalConfig> {
    return this.request('/config/signal', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getNewsSources(): Promise<NewsSource[]> {
    return this.request('/config/sources');
  }

  async updateNewsSource(id: number, source: Partial<NewsSource>): Promise<NewsSource> {
    return this.request(`/config/sources/${id}`, {
      method: 'PUT',
      body: JSON.stringify(source),
    });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
