import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Signal, Ticker, TickerUpdate } from '../types/index';

// ✅ Type aliases for convenience
type SignalsResponse = { signals: Signal[]; total: number };
type NewsResponse = { news: any[]; total: number };
type SentimentSnapshot = any;
type TechnicalData = any;

interface SignalsParams {
  status?: string;
  limit?: number;
}

interface NewsParams {
  ticker_symbol?: string;
  sentiment?: string;
  limit?: number;
}

// ==========================================
// SIGNALS HOOKS
// ==========================================

export function useSignals(params: SignalsParams): UseQueryResult<SignalsResponse> {
  return useQuery({
    queryKey: ['signals', params],
    queryFn: () => apiClient.getSignals(params),
  });
}

export function useSignal(tickerId: number): UseQueryResult<Signal> {
  return useQuery({
    queryKey: ['signal', tickerId],
    queryFn: () => apiClient.getSignal(tickerId),
  });
}

// ==========================================
// NEWS HOOKS
// ==========================================

export function useNews(params: NewsParams): UseQueryResult<NewsResponse> {
  return useQuery({
    queryKey: ['news', params.ticker_symbol, params.sentiment, params.limit],
    queryFn: () => apiClient.getNews(params),
    staleTime: 0,      // Always consider data stale
    gcTime: 0,         // Don't cache (React Query v5)
    refetchOnMount: true,
  });
}

export function useSentiment(tickerId: number): UseQueryResult<SentimentSnapshot> {
  return useQuery({
    queryKey: ['sentiment', tickerId],
    queryFn: () => apiClient.getSentiment(tickerId),
  });
}

export function useTechnicalAnalysis(tickerId: number): UseQueryResult<TechnicalData> {
  return useQuery({
    queryKey: ['technical', tickerId],
    queryFn: () => apiClient.getTechnical(tickerId),
  });
}

// ==========================================
// TICKER MANAGEMENT HOOKS (NEW)
// ==========================================

export function useTickers(isActive?: boolean): UseQueryResult<Ticker[]> {
  return useQuery({
    queryKey: ['tickers', isActive],
    queryFn: async () => {
      return await apiClient.getTickers();
    },
  });
}

export function useTickerDetails(id: number): UseQueryResult<Ticker> {
  return useQuery({
    queryKey: ['ticker', id],
    queryFn: () => apiClient.getTicker(id),
    enabled: !!id,
  });
}

export function useUpdateTicker() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TickerUpdate }) => 
      apiClient.updateTicker(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tickers'] });
      queryClient.invalidateQueries({ queryKey: ['ticker', variables.id] });
    },
  });
}

export function useToggleTickerActive() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: number) => apiClient.toggleTickerActive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickers'] });
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
