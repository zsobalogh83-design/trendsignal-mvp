import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Signal, Ticker, TickerUpdate, StartRunRequest } from '../types/index';

// ✅ Type aliases for convenience
type SignalsResponse = { signals: Signal[]; total: number };
type NewsResponse = { news: any[]; total: number };
type SentimentSnapshot = any;
type TechnicalData = any;

interface SignalsParams {
  status?: string;
  limit?: number;
  latest_per_ticker?: boolean;
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

// ==========================================
// OPTIMIZER HOOKS
// ==========================================

/** Optimizer status (idle panel data). Futás közben 5s, egyébként 30s. */
export function useOptimizerStatus() {
  return useQuery({
    queryKey: ['optimizer-status'],
    queryFn: () => apiClient.getOptimizerStatus(),
    refetchInterval: (query) =>
      (query.state.data as any)?.optimizer_running ? 5_000 : 30_000,
  });
}

/** Live progress for an active run. Polls every 3s when enabled. */
export function useOptimizerProgress(runId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['optimizer-progress', runId],
    queryFn: () => apiClient.getOptimizerProgress(runId!),
    enabled: !!runId && enabled,
    refetchInterval: 3_000,
    staleTime: 0,
  });
}

/** List of recent runs. */
export function useOptimizerRuns(limit = 10) {
  return useQuery({
    queryKey: ['optimizer-runs', limit],
    queryFn: () => apiClient.getOptimizerRuns(limit),
    staleTime: 5_000,
  });
}

/** Proposals for a specific run (or latest). */
export function useProposals(runId?: number) {
  return useQuery({
    queryKey: ['optimizer-proposals', runId],
    queryFn: () => apiClient.getProposals(runId, 10),
    staleTime: 5_000,
  });
}

/** Single proposal detail. */
export function useProposal(proposalId: number | null) {
  return useQuery({
    queryKey: ['optimizer-proposal', proposalId],
    queryFn: () => apiClient.getProposal(proposalId!),
    enabled: !!proposalId,
    staleTime: 60_000,
  });
}

/** Start optimizer run mutation. */
export function useStartOptimizer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: StartRunRequest) => apiClient.startOptimizer(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizer-status'] });
      queryClient.invalidateQueries({ queryKey: ['optimizer-runs'] });
    },
  });
}

/** Stop optimizer mutation. */
export function useStopOptimizer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => apiClient.stopOptimizer(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizer-status'] });
    },
  });
}

/** Approve proposal mutation. Accepts optional versionName for config versioning. */
export function useApproveProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ proposalId, versionName }: { proposalId: number; versionName?: string }) =>
      apiClient.approveProposal(proposalId, versionName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizer-proposals'] });
      queryClient.invalidateQueries({ queryKey: ['optimizer-status'] });
      queryClient.invalidateQueries({ queryKey: ['config-versions'] });
      queryClient.invalidateQueries({ queryKey: ['config-version-active'] });
    },
  });
}

/** Reject proposal mutation. */
export function useRejectProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (proposalId: number) => apiClient.rejectProposal(proposalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimizer-proposals'] });
    },
  });
}

/** Config versions list. */
export function useConfigVersions() {
  return useQuery({
    queryKey: ['config-versions'],
    queryFn: () => apiClient.getConfigVersions(),
    staleTime: 5_000,
  });
}

/** Currently active config version. */
export function useActiveConfigVersion() {
  return useQuery({
    queryKey: ['config-version-active'],
    queryFn: () => apiClient.getActiveConfigVersion(),
    staleTime: 0,
  });
}

/** Create config version mutation. */
export function useCreateConfigVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, source }: { name: string; source?: string }) =>
      apiClient.createConfigVersion(name, source),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-versions'] });
      queryClient.invalidateQueries({ queryKey: ['config-version-active'] });
    },
  });
}

/** Restore config version mutation. */
export function useRestoreConfigVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.restoreConfigVersion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-versions'] });
      queryClient.invalidateQueries({ queryKey: ['config-version-active'] });
    },
  });
}
