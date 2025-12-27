import { useParams, Link } from 'react-router-dom';
import { useSignal, useSentiment, useTechnicalAnalysis } from '../../hooks/useApi';
import {
  formatPrice,
  formatPercent,
  formatTimeAgo,
  getSignalBadgeClass,
  getSignalIcon,
} from '../../utils/helpers';
import {
  FiArrowLeft,
  FiTrendingUp,
  FiTrendingDown,
  FiAlertCircle,
} from 'react-icons/fi';

export function SignalDetail() {
  const { } = useParams<{ tickerSymbol: string }>();
  
  // Assuming we have a way to get ticker ID from symbol
  const tickerId = 1; // This should be fetched from API or context

  const { data: signal, isLoading, error } = useSignal(tickerId);
  const { data: sentiment } = useSentiment(tickerId);
  const { data: technical } = useTechnicalAnalysis(tickerId);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !signal) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Error loading signal details
          </div>
        </div>
      </div>
    );
  }

  const badgeClass = getSignalBadgeClass(signal.decision, signal.strength);
  const icon = getSignalIcon(signal.decision);
  const takeProfitChange = ((signal.take_profit - signal.entry_price) / signal.entry_price) * 100;
  const stopLossChange = ((signal.stop_loss - signal.entry_price) / signal.entry_price) * 100;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-8 py-6">
          <Link
            to="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 mb-4"
          >
            <FiArrowLeft className="mr-2" />
            Back to Dashboard
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {signal.ticker_symbol}
              </h1>
              <span className={`inline-flex items-center px-4 py-2 rounded-full text-base font-semibold ${badgeClass} mt-3`}>
                <span className="mr-2">{icon}</span>
                {signal.strength} {signal.decision} SIGNAL
              </span>
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-600">
            Generated: {formatTimeAgo(signal.created_at)} | Expires: {formatTimeAgo(signal.expires_at)}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Combined Score */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">Combined Score</h2>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <div className="text-5xl font-bold text-gray-900">
                    {signal.combined_score > 0 ? '+' : ''}
                    {signal.combined_score.toFixed(1)}
                  </div>
                  <div className="text-gray-600 mt-2">Score</div>
                </div>
                <div>
                  <div className="text-5xl font-bold text-blue-600">
                    {(signal.overall_confidence * 100).toFixed(0)}%
                  </div>
                  <div className="text-gray-600 mt-2">Confidence</div>
                  <div className="w-full bg-gray-200 rounded-full h-3 mt-3">
                    <div
                      className="bg-blue-600 h-3 rounded-full"
                      style={{ width: `${signal.overall_confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Score Breakdown */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">Score Breakdown</h2>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">Sentiment</span>
                    <span className="text-gray-600">
                      {signal.sentiment_score > 0 ? '+' : ''}
                      {signal.sentiment_score.toFixed(1)} (70% weight)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full"
                      style={{ width: `${((signal.sentiment_score + 100) / 2)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">Technical</span>
                    <span className="text-gray-600">
                      {signal.technical_score > 0 ? '+' : ''}
                      {signal.technical_score.toFixed(1)} (20% weight)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${((signal.technical_score + 100) / 2)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">Risk</span>
                    <span className="text-gray-600">
                      {signal.risk_score > 0 ? '+' : ''}
                      {signal.risk_score.toFixed(1)} (10% weight)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-500 h-2 rounded-full"
                      style={{ width: `${((signal.risk_score + 100) / 2)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Sentiment Analysis */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">📰 Sentiment Analysis</h2>
              <div className="mb-4">
                <p className="text-gray-700">{signal.reasoning.sentiment.summary}</p>
              </div>
              {sentiment && (
                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  <div>
                    <div className="text-gray-600">Weighted Average</div>
                    <div className="text-lg font-semibold">
                      {sentiment.weighted_avg > 0 ? '+' : ''}
                      {sentiment.weighted_avg.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600">News Count</div>
                    <div className="text-lg font-semibold">{sentiment.news_count}</div>
                  </div>
                </div>
              )}
              <div className="space-y-2">
                <h3 className="font-medium text-gray-900">Key News:</h3>
                {signal.reasoning.sentiment.key_news.map((news: string, idx: number) => (
                  <div key={idx} className="flex items-start text-sm">
                    <span className="text-green-500 mr-2">•</span>
                    <span className="text-gray-700">{news}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Technical Analysis */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">📈 Technical Analysis</h2>
              <div className="mb-4">
                <p className="text-gray-700">{signal.reasoning.technical.summary}</p>
              </div>
              <div className="space-y-2">
                <h3 className="font-medium text-gray-900">Key Signals:</h3>
                {signal.reasoning.technical.key_signals.map((sig: string, idx: number) => (
                  <div key={idx} className="flex items-start text-sm">
                    {signal.decision === 'BUY' ? (
                      <FiTrendingUp className="mr-2 mt-0.5 text-green-500" />
                    ) : (
                      <FiTrendingDown className="mr-2 mt-0.5 text-red-500" />
                    )}
                    <span className="text-gray-700">{sig}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Risk Assessment */}
            {signal.reasoning.risk && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-xl font-semibold mb-4">🛡️ Risk Assessment</h2>
                <div className="mb-4">
                  <p className="text-gray-700">{signal.reasoning.risk.summary}</p>
                </div>
                <div className="space-y-2">
                  {signal.reasoning.risk.factors.map((factor: string, idx: number) => (
                    <div key={idx} className="flex items-start text-sm">
                      <FiAlertCircle className="mr-2 mt-0.5 text-yellow-500" />
                      <span className="text-gray-700">{factor}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Entry & Exit Levels */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4">💰 Entry & Exit Levels</h2>
              <div className="space-y-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Entry Price</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {formatPrice(signal.entry_price)}
                  </div>
                </div>

                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Take-Profit</div>
                  <div className="text-2xl font-bold text-green-600">
                    {formatPrice(signal.take_profit)}
                  </div>
                  <div className="text-sm text-green-700 mt-1">
                    {formatPercent(takeProfitChange)}
                  </div>
                </div>

                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Stop-Loss</div>
                  <div className="text-2xl font-bold text-red-600">
                    {formatPrice(signal.stop_loss)}
                  </div>
                  <div className="text-sm text-red-700 mt-1">
                    {formatPercent(stopLossChange)}
                  </div>
                </div>

                <div className="border-t pt-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Risk/Reward Ratio</span>
                    <span className="font-semibold">1:{signal.risk_reward_ratio.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            {technical && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-xl font-semibold mb-4">Technical Indicators</h2>
                <div className="space-y-3 text-sm">
                  {technical.indicators.sma_20 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">SMA 20</span>
                      <span className="font-medium">{formatPrice(technical.indicators.sma_20)}</span>
                    </div>
                  )}
                  {technical.indicators.sma_50 && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">SMA 50</span>
                      <span className="font-medium">{formatPrice(technical.indicators.sma_50)}</span>
                    </div>
                  )}
                  {technical.indicators.rsi && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">RSI</span>
                      <span className="font-medium">{technical.indicators.rsi.toFixed(1)}</span>
                    </div>
                  )}
                  {technical.indicators.macd && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">MACD</span>
                      <span className="font-medium">{technical.indicators.macd.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

