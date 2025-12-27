import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Ticker, SentimentConfig, SignalConfig } from '../types/index';

// Tickers
export function useTickers() {
  return useQuery({
    queryKey: ['tickers'],
    queryFn: () => apiClient.getTickers(),
  });
}

export function useTicker(id: number) {
  return useQuery({
    queryKey: ['ticker', id],
    queryFn: () => apiClient.getTicker(id),
    enabled: !!id,
  });
}

export function useCreateTicker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ticker: Partial<Ticker>) => apiClient.createTicker(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickers'] });
    },
  });
}

export function useUpdateTicker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ticker }: { id: number; ticker: Partial<Ticker> }) =>
      apiClient.updateTicker(id, ticker),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tickers'] });
      queryClient.invalidateQueries({ queryKey: ['ticker', variables.id] });
    },
  });
}

export function useDeleteTicker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.deleteTicker(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickers'] });
    },
  });
}

// Signals
export function useSignals(params?: { status?: 'active' | 'expired' | 'archived'; limit?: number }) {
  return useQuery({
    queryKey: ['signals', params],
    queryFn: () => apiClient.getSignals(params),
  });
}

export function useSignal(tickerId: number) {
  return useQuery({
    queryKey: ['signal', tickerId],
    queryFn: () => apiClient.getSignal(tickerId),
    enabled: !!tickerId,
  });
}

export function useGenerateSignals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.generateSignals(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}

export function useGenerateSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tickerId: number) => apiClient.generateSignal(tickerId),
    onSuccess: (_, tickerId) => {
      queryClient.invalidateQueries({ queryKey: ['signals'] });
      queryClient.invalidateQueries({ queryKey: ['signal', tickerId] });
    },
  });
}

// News
export function useNews(params: { ticker_id?: number; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['news', params],
    queryFn: () => apiClient.getNews(params),
  });
}

export function useNewsItem(id: number) {
  return useQuery({
    queryKey: ['news', id],
    queryFn: () => apiClient.getNewsItem(id),
    enabled: !!id,
  });
}

export function useCollectNews() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.collectNews(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['news'] });
    },
  });
}

// Sentiment
export function useSentiment(tickerId: number) {
  return useQuery({
    queryKey: ['sentiment', tickerId],
    queryFn: () => apiClient.getSentiment(tickerId),
    enabled: !!tickerId,
  });
}

export function useSentimentHistory(tickerId: number, window: string = '24h') {
  return useQuery({
    queryKey: ['sentiment-history', tickerId, window],
    queryFn: () => apiClient.getSentimentHistory(tickerId, window),
    enabled: !!tickerId,
  });
}

// Technical Analysis
export function useTechnicalAnalysis(tickerId: number) {
  return useQuery({
    queryKey: ['technical', tickerId],
    queryFn: () => apiClient.getTechnicalAnalysis(tickerId),
    enabled: !!tickerId,
  });
}

// Configuration
export function useSentimentConfig() {
  return useQuery({
    queryKey: ['config', 'sentiment'],
    queryFn: () => apiClient.getSentimentConfig(),
  });
}

export function useUpdateSentimentConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: Partial<SentimentConfig>) => apiClient.updateSentimentConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'sentiment'] });
    },
  });
}

export function useSignalConfig() {
  return useQuery({
    queryKey: ['config', 'signal'],
    queryFn: () => apiClient.getSignalConfig(),
  });
}

export function useUpdateSignalConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: Partial<SignalConfig>) => apiClient.updateSignalConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'signal'] });
    },
  });
}

export function useNewsSources() {
  return useQuery({
    queryKey: ['config', 'sources'],
    queryFn: () => apiClient.getNewsSources(),
  });
}

export function useUpdateNewsSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, source }: { id: number; source: any }) =>
      apiClient.updateNewsSource(id, source),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'sources'] });
    },
  });
}
