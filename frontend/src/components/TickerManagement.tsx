import { useState } from 'react';
import { FiEdit2, FiTrash2, FiPlus, FiX, FiCheck, FiToggleLeft, FiToggleRight } from 'react-icons/fi';
import { useTickers, useUpdateTicker, useToggleTickerActive, useDeleteTicker } from '../hooks/useApi';
import type { Ticker, TickerUpdate } from '../types/index';

export function TickerManagement() {
  const { data: tickers = [], isLoading } = useTickers();
  const updateTicker = useUpdateTicker();
  const toggleActive = useToggleTickerActive();
  const deleteTicker = useDeleteTicker();
  
  const [editingTicker, setEditingTicker] = useState<Ticker | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState<TickerUpdate>({});
  
  const handleEdit = (ticker: Ticker) => {
    setEditingTicker(ticker);
    setFormData({
      name: ticker.name,
      market: ticker.market,
      priority: ticker.priority,
      is_active: ticker.is_active,
      primary_language: ticker.primary_language,
      industry: ticker.industry,
      sector: ticker.sector,
      currency: ticker.currency,
      relevance_keywords: [...ticker.relevance_keywords],
      sentiment_keywords_positive: [...ticker.sentiment_keywords_positive],
      sentiment_keywords_negative: [...ticker.sentiment_keywords_negative],
      news_sources_preferred: [...ticker.news_sources_preferred],
      news_sources_blocked: [...ticker.news_sources_blocked],
    });
    setShowModal(true);
  };
  
  const handleSave = async () => {
    if (!editingTicker) return;
    
    try {
      await updateTicker.mutateAsync({ id: editingTicker.id, data: formData });
      setShowModal(false);
      setEditingTicker(null);
    } catch (error) {
      console.error('Failed to update ticker:', error);
      alert('Failed to save changes');
    }
  };
  
  const handleToggle = async (id: number) => {
    try {
      await toggleActive.mutateAsync(id);
    } catch (error) {
      console.error('Failed to toggle ticker:', error);
    }
  };
  
  const handleDelete = async (id: number, symbol: string) => {
    if (!confirm(`Deactivate ${symbol}?`)) return;
    try {
      await deleteTicker.mutateAsync(id);
    } catch (error) {
      console.error('Failed to delete ticker:', error);
    }
  };
  
  const addKeyword = (field: keyof TickerUpdate, value: string) => {
    if (!value.trim()) return;
    const currentList = (formData[field] as string[]) || [];
    if (!currentList.includes(value.trim())) {
      setFormData({ ...formData, [field]: [...currentList, value.trim()] });
    }
  };
  
  const removeKeyword = (field: keyof TickerUpdate, value: string) => {
    const currentList = (formData[field] as string[]) || [];
    setFormData({ ...formData, [field]: currentList.filter(k => k !== value) });
  };
  
  const getPriorityBadge = (priority: string) => {
    const styles = {
      high: { bg: 'rgba(239, 68, 68, 0.2)', text: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' },
      medium: { bg: 'rgba(251, 191, 36, 0.2)', text: '#fbbf24', border: 'rgba(251, 191, 36, 0.3)' },
      low: { bg: 'rgba(148, 163, 184, 0.2)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' },
    };
    const style = styles[priority as keyof typeof styles] || styles.medium;
    return (
      <span style={{ padding: '4px 12px', borderRadius: '12px', fontSize: '12px', fontWeight: '600',
        background: style.bg, color: style.text, border: `1px solid ${style.border}` }}>
        {priority === 'high' ? '🔴' : priority === 'medium' ? '🟡' : '⚪'} {priority.toUpperCase()}
      </span>
    );
  };
  
  const getMarketFlag = (market: string) => {
    if (market === 'BET') return '🇭🇺';
    if (market === 'NYSE' || market === 'NASDAQ') return '🇺🇸';
    return '🌍';
  };
  
  if (isLoading) return <div style={{ color: '#94a3b8', padding: '20px' }}>Loading tickers...</div>;
  
  return (
    <div>
      <div style={{ background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '16px', padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '18px', fontWeight: '700', color: '#f1f5f9', marginBottom: '8px' }}>
              📊 Ticker Management
            </div>
            <div style={{ fontSize: '13px', color: '#64748b' }}>
              Configure ticker symbols, keywords, and news sources
            </div>
          </div>
          <button onClick={() => alert('Add new ticker feature coming soon')} style={{
            padding: '10px 20px', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.5)',
            background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', cursor: 'pointer',
            fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FiPlus size={16} /> Add Ticker
          </button>
        </div>
      </div>
      
      <div style={{ background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '16px', padding: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.5)' }}>
              {['Symbol', 'Name', 'Market', 'Priority', 'Status', 'Actions'].map(header => (
                <th key={header} style={{ padding: '12px 16px', textAlign: 'left', fontSize: '13px',
                  color: '#94a3b8', fontWeight: '600' }}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tickers.map((ticker, idx) => (
              <tr key={ticker.id} style={{ borderBottom: idx < tickers.length - 1 ? '1px solid rgba(51, 65, 85, 0.3)' : 'none',
                transition: 'background 0.2s' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(51, 65, 85, 0.3)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '18px' }}>{getMarketFlag(ticker.market)}</span>
                    <strong style={{ color: '#60a5fa', fontSize: '14px' }}>{ticker.symbol}</strong>
                  </div>
                </td>
                <td style={{ padding: '14px 16px', fontSize: '14px', color: '#cbd5e1' }}>{ticker.name || '-'}</td>
                <td style={{ padding: '14px 16px', fontSize: '13px', color: '#94a3b8' }}>{ticker.market || '-'}</td>
                <td style={{ padding: '14px 16px' }}>{getPriorityBadge(ticker.priority)}</td>
                <td style={{ padding: '14px 16px' }}>
                  <button onClick={() => handleToggle(ticker.id)} style={{
                    display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '8px',
                    border: ticker.is_active ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(148, 163, 184, 0.3)',
                    background: ticker.is_active ? 'rgba(16, 185, 129, 0.1)' : 'rgba(51, 65, 85, 0.3)',
                    color: ticker.is_active ? '#10b981' : '#64748b', cursor: 'pointer',
                    fontSize: '13px', fontWeight: '600' }}>
                    {ticker.is_active ? <FiToggleRight size={16} /> : <FiToggleLeft size={16} />}
                    {ticker.is_active ? 'Active' : 'Inactive'}
                  </button>
                </td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => handleEdit(ticker)} style={{
                      padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                      background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', cursor: 'pointer',
                      fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FiEdit2 size={14} /> Edit
                    </button>
                    <button onClick={() => handleDelete(ticker.id, ticker.symbol)} style={{
                      padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)',
                      background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', cursor: 'pointer',
                      fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FiTrash2 size={14} /> Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {showModal && editingTicker && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, animation: 'fadeIn 0.2s ease-out' }}
          onClick={() => setShowModal(false)}>
          <div style={{ background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)',
            border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '16px', padding: '32px',
            maxWidth: '700px', width: '90%', maxHeight: '90vh', overflowY: 'auto' }}
            onClick={(e) => e.stopPropagation()}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <div>
                <div style={{ fontSize: '20px', fontWeight: '700', color: '#f1f5f9' }}>
                  Edit Ticker: {editingTicker.symbol}
                </div>
                <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                  Configure keywords, sources, and settings
                </div>
              </div>
              <button onClick={() => setShowModal(false)} style={{
                background: 'none', border: 'none', color: '#64748b', fontSize: '24px', cursor: 'pointer', padding: '4px' }}>
                <FiX size={24} />
              </button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div style={{ background: 'rgba(51, 65, 85, 0.3)', border: '1px solid rgba(99, 102, 241, 0.2)',
                borderRadius: '12px', padding: '20px' }}>
                <div style={{ fontSize: '16px', fontWeight: '600', color: '#f1f5f9', marginBottom: '16px' }}>
                  📝 Basic Information
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Name</label>
                    <input type="text" value={formData.name || ''} onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.3)',
                        background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '14px' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Market</label>
                    <select value={formData.market || ''} onChange={(e) => setFormData({ ...formData, market: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.3)',
                        background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '14px' }}>
                      <option value="">Select...</option>
                      <option value="BET">🇭🇺 BÉT</option>
                      <option value="NYSE">🇺🇸 NYSE</option>
                      <option value="NASDAQ">🇺🇸 NASDAQ</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Priority</label>
                    <select value={formData.priority || 'medium'} onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.3)',
                        background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '14px' }}>
                      <option value="high">🔴 High</option>
                      <option value="medium">🟡 Medium</option>
                      <option value="low">⚪ Low</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Language</label>
                    <select value={formData.primary_language || 'en'} onChange={(e) => setFormData({ ...formData, primary_language: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.3)',
                        background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '14px' }}>
                      <option value="en">🇬🇧 English</option>
                      <option value="hu">🇭🇺 Hungarian</option>
                    </select>
                  </div>
                </div>
              </div>
              
              <KeywordEditor title="🔤 Relevance Keywords" description="Keywords to identify relevant news"
                keywords={formData.relevance_keywords || []} onAdd={(v) => addKeyword('relevance_keywords', v)}
                onRemove={(v) => removeKeyword('relevance_keywords', v)} />
              
              <KeywordEditor title="😊 Positive Sentiment Keywords" description="Boost positive sentiment"
                keywords={formData.sentiment_keywords_positive || []} onAdd={(v) => addKeyword('sentiment_keywords_positive', v)}
                onRemove={(v) => removeKeyword('sentiment_keywords_positive', v)} color="green" />
              
              <KeywordEditor title="😞 Negative Sentiment Keywords" description="Boost negative sentiment"
                keywords={formData.sentiment_keywords_negative || []} onAdd={(v) => addKeyword('sentiment_keywords_negative', v)}
                onRemove={(v) => removeKeyword('sentiment_keywords_negative', v)} color="red" />
              
              <KeywordEditor title="📰 Preferred News Sources" description="Prioritize these sources"
                keywords={formData.news_sources_preferred || []} onAdd={(v) => addKeyword('news_sources_preferred', v)}
                onRemove={(v) => removeKeyword('news_sources_preferred', v)} color="blue" />
              
              <KeywordEditor title="🚫 Blocked News Sources" description="Ignore these sources"
                keywords={formData.news_sources_blocked || []} onAdd={(v) => addKeyword('news_sources_blocked', v)}
                onRemove={(v) => removeKeyword('news_sources_blocked', v)} color="gray" />
            </div>
            
            <div style={{ display: 'flex', gap: '12px', marginTop: '32px', paddingTop: '24px',
              borderTop: '1px solid rgba(51, 65, 85, 0.5)' }}>
              <button onClick={() => setShowModal(false)} style={{
                flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.3)',
                background: 'rgba(51, 65, 85, 0.5)', color: '#cbd5e1', cursor: 'pointer',
                fontSize: '14px', fontWeight: '600' }}>Cancel</button>
              
              <button onClick={handleSave} disabled={updateTicker.isPending} style={{
                flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.5)',
                background: updateTicker.isPending ? 'rgba(51, 65, 85, 0.5)' : 'rgba(16, 185, 129, 0.2)',
                color: updateTicker.isPending ? '#64748b' : '#10b981',
                cursor: updateTicker.isPending ? 'not-allowed' : 'pointer',
                fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: '8px' }}>
                <FiCheck size={16} /> {updateTicker.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      <style>{`@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }`}</style>
    </div>
  );
}

interface KeywordEditorProps {
  title: string;
  description: string;
  keywords: string[];
  onAdd: (value: string) => void;
  onRemove: (value: string) => void;
  color?: 'blue' | 'green' | 'red' | 'gray';
}

function KeywordEditor({ title, description, keywords, onAdd, onRemove, color = 'blue' }: KeywordEditorProps) {
  const [newKeyword, setNewKeyword] = useState('');
  const colorStyles = {
    blue: { bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.3)', text: '#3b82f6' },
    green: { bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.3)', text: '#10b981' },
    red: { bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.3)', text: '#ef4444' },
    gray: { bg: 'rgba(148, 163, 184, 0.1)', border: 'rgba(148, 163, 184, 0.3)', text: '#94a3b8' },
  };
  const style = colorStyles[color];
  
  const handleAdd = () => {
    if (newKeyword.trim()) {
      onAdd(newKeyword.trim());
      setNewKeyword('');
    }
  };
  
  return (
    <div style={{ background: 'rgba(51, 65, 85, 0.3)', border: `1px solid ${style.border}`,
      borderRadius: '12px', padding: '20px' }}>
      <div style={{ fontSize: '16px', fontWeight: '600', color: '#f1f5f9', marginBottom: '6px' }}>{title}</div>
      <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '16px' }}>{description}</div>
      
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <input type="text" value={newKeyword} onChange={(e) => setNewKeyword(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleAdd()} placeholder="Type and press Enter..."
          style={{ flex: 1, padding: '10px 12px', borderRadius: '8px', border: `1px solid ${style.border}`,
            background: 'rgba(15, 23, 42, 0.6)', color: '#f1f5f9', fontSize: '14px' }} />
        <button onClick={handleAdd} style={{
          padding: '10px 16px', borderRadius: '8px', border: `1px solid ${style.border}`,
          background: style.bg, color: style.text, cursor: 'pointer', fontSize: '14px',
          fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FiPlus size={16} /> Add
        </button>
      </div>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {keywords.length === 0 && (
          <div style={{ fontSize: '13px', color: '#64748b', fontStyle: 'italic' }}>No keywords defined yet</div>
        )}
        {keywords.map((keyword, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', borderRadius: '8px', background: style.bg,
            border: `1px solid ${style.border}`, color: style.text, fontSize: '13px', fontWeight: '500' }}>
            <span>{keyword}</span>
            <button onClick={() => onRemove(keyword)} style={{
              background: 'none', border: 'none', color: style.text, cursor: 'pointer',
              padding: '0', display: 'flex', alignItems: 'center' }}>
              <FiX size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
