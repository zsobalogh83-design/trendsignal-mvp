import { useState } from 'react';
import { useSignals } from '../../hooks';
import { SignalCard } from '../../components/SignalCard/SignalCard';
import type { Signal } from '../../types';
import { FiFilter, FiRefreshCw } from 'react-icons/fi';

export function Dashboard() {
  const [statusFilter, setStatusFilter] = useState<'active' | 'expired' | 'archived'>('active');
  const [decisionFilter, setDecisionFilter] = useState<string>('all');
  const [strengthFilter, setStrengthFilter] = useState<string>('all');

  const { data, isLoading, error, refetch } = useSignals({ status: statusFilter, limit: 50 });

  const filteredSignals = data?.signals.filter((signal: Signal) => {
    if (decisionFilter !== 'all' && signal.decision !== decisionFilter) return false;
    if (strengthFilter !== 'all' && signal.strength !== strengthFilter) return false;
    return true;
  }) || [];

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Error loading signals: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">TrendSignal</h1>
              <p className="text-gray-600 mt-1">Trading Signals Dashboard</p>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              <FiRefreshCw className={isLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-6">
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <FiFilter className="text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
            </div>

            <div>
              <label className="text-sm text-gray-600 mr-2">Status:</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="active">Active</option>
                <option value="expired">Expired</option>
                <option value="archived">Archived</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-gray-600 mr-2">Decision:</label>
              <select
                value={decisionFilter}
                onChange={(e) => setDecisionFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All</option>
                <option value="BUY">Buy</option>
                <option value="SELL">Sell</option>
                <option value="HOLD">Hold</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-gray-600 mr-2">Strength:</label>
              <select
                value={strengthFilter}
                onChange={(e) => setStrengthFilter(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All</option>
                <option value="STRONG">Strong</option>
                <option value="MODERATE">Moderate</option>
                <option value="WEAK">Weak</option>
              </select>
            </div>

            <div className="ml-auto text-sm text-gray-600">
              {filteredSignals.length} signal{filteredSignals.length !== 1 ? 's' : ''}
            </div>
          </div>
        </div>

        {isLoading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-gray-600 mt-4">Loading signals...</p>
          </div>
        )}

        {!isLoading && filteredSignals.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No signals found</h3>
            <p className="text-gray-600">
              Try adjusting your filters or generate new signals.
            </p>
          </div>
        )}

        {!isLoading && filteredSignals.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSignals.map((signal: Signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
