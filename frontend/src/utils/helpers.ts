import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatPrice(price: number, currency: string = 'HUF'): string {
  return new Intl.NumberFormat('hu-HU', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(price);
}

export function formatPercent(value: number, decimals: number = 2): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'most';
  if (diffMins < 60) return `${diffMins} perce`;
  if (diffHours < 24) return `${diffHours} órája`;
  if (diffDays < 7) return `${diffDays} napja`;
  
  return date.toLocaleDateString('hu-HU');
}

export function getSignalColor(decision: string, strength?: string): string {
  if (decision === 'BUY') {
    return strength === 'STRONG' ? 'text-green-600' : 'text-green-500';
  }
  if (decision === 'SELL') {
    return strength === 'STRONG' ? 'text-red-600' : 'text-red-500';
  }
  return 'text-gray-500';
}

export function getSignalBadgeClass(decision: string, strength?: string): string {
  if (decision === 'BUY') {
    return strength === 'STRONG'
      ? 'bg-green-100 text-green-800'
      : 'bg-green-50 text-green-700';
  }
  if (decision === 'SELL') {
    return strength === 'STRONG'
      ? 'bg-red-100 text-red-800'
      : 'bg-red-50 text-red-700';
  }
  return 'bg-gray-100 text-gray-600';
}

export function getSignalIcon(decision: string): string {
  if (decision === 'BUY') return '🟢';
  if (decision === 'SELL') return '🔴';
  return '⚪';
}

export function calculateRiskRewardRatio(
  entryPrice: number,
  stopLoss: number,
  takeProfit: number
): number {
  const risk = Math.abs(entryPrice - stopLoss);
  const reward = Math.abs(takeProfit - entryPrice);
  return reward / risk;
}

export function formatRiskReward(ratio: number): string {
  return `1:${ratio.toFixed(1)}`;
}

export function scoreToPercentage(score: number): number {
  // Convert -100 to +100 score to 0-100 percentage
  return ((score + 100) / 2);
}

export function confidenceToPercentage(confidence: number): number {
  // Convert 0.0-1.0 to 0-100
  return confidence * 100;
}
