import { Link } from 'react-router-dom';
import type { Signal } from '../../types/index';
import {
  formatPrice,
  formatPercent,
  formatTimeAgo,
  getSignalBadgeClass,
  getSignalIcon,
} from '../../utils/helpers';
import { FiTrendingUp, FiTrendingDown, FiClock, FiInfo } from 'react-icons/fi';

interface SignalCardProps {
  signal: Signal;
}

export function SignalCard({ signal }: SignalCardProps) {
  const badgeClass = getSignalBadgeClass(signal.decision, signal.strength);
  const icon = getSignalIcon(signal.decision);
  
  const priceChange = ((signal.take_profit - signal.entry_price) / signal.entry_price) * 100;
  const stopLossChange = ((signal.stop_loss - signal.entry_price) / signal.entry_price) * 100;

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {signal.ticker_symbol}
            </h3>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${badgeClass} mt-2`}>
              <span className="mr-1">{icon}</span>
              {signal.strength} {signal.decision}
            </span>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Score</div>
            <div className="text-2xl font-bold text-gray-900">
              {signal.combined_score > 0 ? '+' : ''}
              {signal.combined_score.toFixed(1)}
            </div>
          </div>
        </div>

        {/* Confidence */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Confidence</span>
            <span className="font-medium">
              {(signal.overall_confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${signal.overall_confidence * 100}%` }}
            />
          </div>
        </div>

        {/* Score Breakdown */}
        <div className="space-y-2 mb-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Sentiment:</span>
            <span className="font-medium">
              {signal.sentiment_score > 0 ? '+' : ''}
              {signal.sentiment_score.toFixed(1)} (70%)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Technical:</span>
            <span className="font-medium">
              {signal.technical_score > 0 ? '+' : ''}
              {signal.technical_score.toFixed(1)} (20%)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Risk:</span>
            <span className="font-medium">
              {signal.risk_score > 0 ? '+' : ''}
              {signal.risk_score.toFixed(1)} (10%)
            </span>
          </div>
        </div>

        <div className="border-t pt-4 mb-4">
          {/* Price Levels */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Entry:</span>
              <span className="font-semibold">
                {formatPrice(signal.entry_price)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Target:</span>
              <span className="font-semibold text-green-600">
                {formatPrice(signal.take_profit)}
                <span className="ml-2 text-xs">
                  ({formatPercent(priceChange)})
                </span>
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Stop-loss:</span>
              <span className="font-semibold text-red-600">
                {formatPrice(signal.stop_loss)}
                <span className="ml-2 text-xs">
                  ({formatPercent(stopLossChange)})
                </span>
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">R:R Ratio:</span>
              <span className="font-semibold">
                1:{signal.risk_reward_ratio.toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Insights */}
        <div className="space-y-1 mb-4 text-xs text-gray-600">
          {signal.reasoning.sentiment.key_news.slice(0, 2).map((news, idx) => (
            <div key={idx} className="flex items-start">
              <FiInfo className="mr-1 mt-0.5 flex-shrink-0" />
              <span className="line-clamp-1">{news}</span>
            </div>
          ))}
          {signal.reasoning.technical.key_signals.slice(0, 1).map((sig, idx) => (
            <div key={idx} className="flex items-start">
              {signal.decision === 'BUY' ? (
                <FiTrendingUp className="mr-1 mt-0.5 flex-shrink-0 text-green-500" />
              ) : (
                <FiTrendingDown className="mr-1 mt-0.5 flex-shrink-0 text-red-500" />
              )}
              <span className="line-clamp-1">{sig}</span>
            </div>
          ))}
        </div>

        {/* Timestamp */}
        <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
          <div className="flex items-center">
            <FiClock className="mr-1" />
            {formatTimeAgo(signal.created_at)}
          </div>
          <div>
            Expires: {formatTimeAgo(signal.expires_at)}
          </div>
        </div>

        {/* Actions */}
        <Link
          to={`/signal/${signal.ticker_symbol}`}
          className="block w-full text-center bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          View Details
        </Link>
      </div>
    </div>
  );
}
