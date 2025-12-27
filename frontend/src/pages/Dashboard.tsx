import { useState } from 'react';
import { useSignals } from '../hooks/useApi';
import { FiFilter, FiRefreshCw } from 'react-icons/fi';

export function Dashboard() {
  const { data, isLoading, error, refetch } = useSignals({ status: 'active', limit: 50 });

  if (error) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', padding: '32px' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '16px', color: '#991b1b' }}>
            Error loading signals: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ border: '4px solid #e5e7eb', borderTop: '4px solid #2563eb', borderRadius: '50%', width: '48px', height: '48px', animation: 'spin 1s linear infinite', margin: '0 auto' }}></div>
          <p style={{ color: '#6b7280', marginTop: '16px' }}>Loading signals...</p>
        </div>
      </div>
    );
  }

  const signals = data?.signals || [];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      <div style={{ backgroundColor: 'white', borderBottom: '1px solid #e5e7eb' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: '30px', fontWeight: 'bold', color: '#111827', margin: 0 }}>TrendSignal</h1>
              <p style={{ color: '#6b7280', marginTop: '4px' }}>Trading Signals Dashboard</p>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              <FiRefreshCw style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 32px' }}>
        {signals.length === 0 ? (
          <div style={{ textAlign: 'center', paddingTop: '48px', paddingBottom: '48px' }}>
            <div style={{ fontSize: '60px', color: '#d1d5db', marginBottom: '16px' }}>📊</div>
            <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#374151', marginBottom: '8px' }}>No signals found</h3>
            <p style={{ color: '#6b7280' }}>
              The backend API is not returning any signals. Check if the backend is running on http://localhost:8000
            </p>
          </div>
        ) : (
          <div>
            <p style={{ color: '#10b981', fontSize: '18px', fontWeight: '600' }}>
              ✅ {signals.length} signals loaded successfully!
            </p>
            <pre style={{ backgroundColor: '#f3f4f6', padding: '16px', borderRadius: '8px', overflow: 'auto', fontSize: '12px' }}>
              {JSON.stringify(signals[0], null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
