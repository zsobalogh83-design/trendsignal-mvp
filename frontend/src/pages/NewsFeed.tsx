import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useNews } from '../hooks/useApi';
import { FiArrowLeft, FiRefreshCw, FiExternalLink } from 'react-icons/fi';

export function NewsFeed() {
  const [searchTerm, setSearchTerm] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  
  const { data, isLoading, error, refetch } = useNews({ 
    ticker_symbol: undefined, 
    sentiment: sentimentFilter === 'all' ? undefined : sentimentFilter,
    limit: 50 
  });

  // Refetch when sentiment filter changes
  useEffect(() => {
    refetch();
  }, [sentimentFilter, refetch]);

  const newsItems = data?.news || [];
  
  const handleRefresh = async () => {
    console.log('Refreshing news...');
    await refetch();
  };

  const filteredNews = newsItems.filter((news: any) => {
    const matchesSearch = searchTerm === '' || 
      news.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      news.description?.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesSearch;
  });

  const getSentimentBadgeClass = (label: string) => {
    if (label === 'positive') return { bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)' };
    if (label === 'negative') return { bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' };
    return { bg: 'rgba(100, 116, 139, 0.2)', color: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)' };
  };

  const getNewsCardBorderColor = (label: string) => {
    if (label === 'positive') return '#10b981';
    if (label === 'negative') return '#ef4444';
    return '#64748b';
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)',
      color: '#e0e7ff',
      padding: '20px'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '20px 0',
          borderBottom: '1px solid rgba(99, 102, 241, 0.2)',
          marginBottom: '30px',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          <Link to="/" style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#60a5fa',
            textDecoration: 'none',
            fontSize: '14px',
            padding: '8px 16px',
            borderRadius: '8px',
            background: 'rgba(59, 130, 246, 0.1)',
            transition: 'all 0.3s'
          }}>
            <FiArrowLeft /> Dashboard
          </Link>

          <div style={{
            fontSize: '28px',
            fontWeight: '700',
            background: 'linear-gradient(135deg, #3b82f6 0%, #10b981 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            📰 News Feed
          </div>

          <button
            onClick={handleRefresh}
            disabled={isLoading}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: 'none',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              color: 'white',
              transition: 'all 0.3s',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: isLoading ? 0.5 : 1
            }}
          >
            <FiRefreshCw style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>

        {/* Filters */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '24px'
        }}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px', fontWeight: '600', display: 'block' }}>
              🔍 Search
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search news by title, content, or keywords..."
              style={{
                width: '100%',
                padding: '12px 16px',
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: '8px',
                color: '#e0e7ff',
                fontSize: '14px',
                transition: 'all 0.3s'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px', fontWeight: '600', display: 'block' }}>
                💭 Sentiment
              </label>
              <select
                value={sentimentFilter}
                onChange={(e) => setSentimentFilter(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'rgba(15, 23, 42, 0.5)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  borderRadius: '8px',
                  color: '#e0e7ff',
                  fontSize: '14px',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Sentiment</option>
                <option value="positive">🟢 Positive Only</option>
                <option value="neutral">⚪ Neutral Only</option>
                <option value="negative">🔴 Negative Only</option>
              </select>
            </div>

            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px', fontWeight: '600', display: 'block' }}>
                📑 Category
              </label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'rgba(15, 23, 42, 0.5)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  borderRadius: '8px',
                  color: '#e0e7ff',
                  fontSize: '14px',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Categories</option>
                <option value="earnings">Earnings</option>
                <option value="analyst">Analyst Ratings</option>
                <option value="regulatory">Regulatory</option>
              </select>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            padding: '20px',
            color: '#ef4444',
            marginBottom: '24px'
          }}>
            Error loading news: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        )}

        {/* Results Summary */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          padding: '12px 16px',
          background: 'rgba(30, 41, 59, 0.5)',
          borderRadius: '8px'
        }}>
          <div style={{ fontSize: '14px', color: '#94a3b8' }}>
            Showing <strong style={{ color: '#60a5fa', fontSize: '16px' }}>{filteredNews.length}</strong> news items
          </div>
        </div>

        {/* News Cards */}
        <div>
          {isLoading && (
            <div style={{ textAlign: 'center', paddingTop: '60px' }}>
              <div style={{ width: '48px', height: '48px', border: '4px solid rgba(59, 130, 246, 0.2)', borderTop: '4px solid #3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto' }}></div>
              <p style={{ color: '#64748b', marginTop: '20px' }}>Loading news...</p>
            </div>
          )}

          {!isLoading && filteredNews.map((news: any) => {
            const sentimentLabel = news.sentiment_label || 'neutral';
            const badgeStyle = getSentimentBadgeClass(sentimentLabel);
            const borderColor = getNewsCardBorderColor(sentimentLabel);

            return (
              <div
                key={news.id}
                style={{
                  background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  borderRadius: '12px',
                  padding: '24px',
                  marginBottom: '16px',
                  borderLeft: `4px solid ${borderColor}`,
                  transition: 'all 0.3s',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#3b82f6';
                  e.currentTarget.style.transform = 'translateX(5px)';
                  e.currentTarget.style.boxShadow = '0 8px 30px rgba(59, 130, 246, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                  e.currentTarget.style.transform = 'translateX(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', gap: '16px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px', lineHeight: '1.4' }}>
                      {sentimentLabel === 'positive' && '🟢 '}
                      {sentimentLabel === 'neutral' && '⚪ '}
                      {sentimentLabel === 'negative' && '🔴 '}
                      {news.title}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', fontSize: '13px', color: '#64748b' }}>
                      <span>📰 {news.source || 'Unknown'}</span>
                      <span>🕐 {new Date(news.published_at).toLocaleString()}</span>
                      <span style={{
                        background: 'rgba(59, 130, 246, 0.2)',
                        color: '#60a5fa',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: '600'
                      }}>
                        {news.ticker_symbol}
                      </span>
                    </div>
                  </div>

                  <div style={{
                    padding: '8px 14px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: '700',
                    background: badgeStyle.bg,
                    color: badgeStyle.color,
                    border: `1px solid ${badgeStyle.border}`,
                    textAlign: 'center'
                  }}>
                    {news.sentiment_score > 0 ? '+' : ''}{news.sentiment_score?.toFixed(2) || '0.00'}
                    <div style={{ fontSize: '10px', opacity: 0.8 }}>
                      {((news.sentiment_confidence || 0) * 100).toFixed(0)}% conf
                    </div>
                  </div>
                </div>

                {/* Excerpt */}
                <div style={{ fontSize: '14px', color: '#cbd5e1', lineHeight: '1.6', marginBottom: '16px' }}>
                  {news.description || news.title}
                </div>

                {/* Footer */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingTop: '16px',
                  borderTop: '1px solid rgba(51, 65, 85, 0.3)',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {news.categories?.map((cat: string, idx: number) => (
                      <span key={idx} style={{
                        background: 'rgba(59, 130, 246, 0.1)',
                        color: '#60a5fa',
                        padding: '4px 10px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '600'
                      }}>
                        {cat}
                      </span>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {news.url && (
                      <a href={news.url} target="_blank" rel="noopener noreferrer" style={{
                        color: '#3b82f6',
                        textDecoration: 'none',
                        fontSize: '13px',
                        fontWeight: '600',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        background: 'rgba(59, 130, 246, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        transition: 'all 0.3s'
                      }}>
                        Read Article <FiExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Load More */}
        {filteredNews.length > 0 && (
          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <button style={{
              padding: '12px 32px',
              borderRadius: '8px',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              background: 'rgba(51, 65, 85, 0.5)',
              color: '#cbd5e1',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}>
              Load More News
            </button>
          </div>
        )}

        {/* Empty State */}
        {filteredNews.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748b' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📰</div>
            <div style={{ fontSize: '16px', marginBottom: '8px' }}>No news found</div>
            <div style={{ fontSize: '13px' }}>Try adjusting your filters</div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
