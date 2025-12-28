import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient, Signal, SignalsResponse, NewsResponse, SentimentSnapshot, TechnicalData } from '../api/client';

interface SignalsParams {
  status?: string;
  limit?: number;
}

interface NewsParams {
  ticker_symbol?: string;
  sentiment?: string;
  limit?: number;
}

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
