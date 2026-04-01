import React, { useEffect, useState } from 'react';
import { checkStatus } from './utils';

const card = {
  background: '#fff',
  borderRadius: '8px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
  padding: '20px 24px',
  marginBottom: '20px'
};

const statBox = {
  display: 'inline-block',
  background: '#f0f4ff',
  borderRadius: '6px',
  padding: '14px 24px',
  margin: '6px',
  minWidth: '160px',
  textAlign: 'center'
};

const statNum = {
  fontSize: '28px',
  fontWeight: '700',
  color: '#2c5282'
};

const statLabel = {
  fontSize: '12px',
  color: '#555',
  marginTop: '4px'
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '13px'
};

const thStyle = {
  background: '#edf2f7',
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: '600',
  borderBottom: '2px solid #cbd5e0'
};

const tdStyle = {
  padding: '7px 12px',
  borderBottom: '1px solid #e2e8f0'
};

const barContainer = {
  background: '#e2e8f0',
  borderRadius: '4px',
  height: '12px',
  minWidth: '80px',
  display: 'inline-block',
  verticalAlign: 'middle',
  marginLeft: '8px'
};

const CaseStatsDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/v1/case_stats')
      .then(checkStatus)
      .then(r => r.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        setError('Failed to load statistics');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#555' }}>
        Loading statistics...
      </div>
    );
  }

  if (error) {
    return <div style={{ padding: '40px', color: '#e53e3e' }}>{error}</div>;
  }

  const maxTypeCount =
    stats.by_type && stats.by_type.length > 0 ? stats.by_type[0].count : 1;
  const maxCourtCount =
    stats.by_court && stats.by_court.length > 0 ? stats.by_court[0].count : 1;
  const maxYearCount =
    stats.by_year && stats.by_year.length > 0
      ? Math.max(...stats.by_year.map(r => r.count))
      : 1;

  return (
    <div style={{ padding: '24px', maxWidth: '1100px', marginLeft: '0' }}>
      <h2 style={{ marginBottom: '20px', color: '#1a202c' }}>
        Case Status Dashboard
      </h2>

      {/* Summary Cards */}
      <div style={card}>
        <h3 style={{ marginBottom: '12px', color: '#2d3748' }}>Overview</h3>
        <div>
          {[
            {
              label: 'Total Cases',
              value:
                stats.totals.total != null
                  ? stats.totals.total.toLocaleString()
                  : '—'
            },
            {
              label: 'Foreclosures',
              value:
                stats.totals.foreclosures != null
                  ? stats.totals.foreclosures.toLocaleString()
                  : '—'
            },
            {
              label: 'Right of Redemption',
              value:
                stats.totals.redemption != null
                  ? stats.totals.redemption.toLocaleString()
                  : '—'
            },
            {
              label: 'Open Cases',
              value:
                stats.totals.open != null
                  ? stats.totals.open.toLocaleString()
                  : '—'
            },
            {
              label: 'Closed Cases',
              value:
                stats.totals.closed != null
                  ? stats.totals.closed.toLocaleString()
                  : '—'
            },
            {
              label: 'Filed in 2025',
              value:
                stats.totals.y2025 != null
                  ? stats.totals.y2025.toLocaleString()
                  : '—'
            },
            {
              label: 'Filed in 2026',
              value:
                stats.totals.y2026 != null
                  ? stats.totals.y2026.toLocaleString()
                  : '—'
            }
          ].map(s => (
            <div key={s.label} style={statBox}>
              <div style={statNum}>{s.value != null ? s.value : '—'}</div>
              <div style={statLabel}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        {/* Top Case Types */}
        <div style={{ ...card, flex: '1 1 460px' }}>
          <h3 style={{ marginBottom: '12px', color: '#2d3748' }}>
            Top Case Types
          </h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Case Type</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Count</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {(stats.by_type || []).slice(0, 20).map((row, i) => (
                <tr
                  key={i}
                  style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}
                >
                  <td style={tdStyle}>{row.case_type}</td>
                  <td
                    style={{
                      ...tdStyle,
                      textAlign: 'right',
                      fontWeight: '600'
                    }}
                  >
                    {row.count.toLocaleString()}
                  </td>
                  <td style={tdStyle}>
                    <div style={barContainer}>
                      <div
                        style={{
                          background: '#4299e1',
                          borderRadius: '4px',
                          height: '12px',
                          width: `${Math.round(
                            (row.count / maxTypeCount) * 100
                          )}%`
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Top Courts */}
        <div style={{ ...card, flex: '1 1 380px' }}>
          <h3 style={{ marginBottom: '12px', color: '#2d3748' }}>Top Courts</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Court</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Count</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {(stats.by_court || []).slice(0, 20).map((row, i) => (
                <tr
                  key={i}
                  style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}
                >
                  <td style={tdStyle}>{row.court_name}</td>
                  <td
                    style={{
                      ...tdStyle,
                      textAlign: 'right',
                      fontWeight: '600'
                    }}
                  >
                    {row.count.toLocaleString()}
                  </td>
                  <td style={tdStyle}>
                    <div style={barContainer}>
                      <div
                        style={{
                          background: '#48bb78',
                          borderRadius: '4px',
                          height: '12px',
                          width: `${Math.round(
                            (row.count / maxCourtCount) * 100
                          )}%`
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Filing by Year */}
      <div style={card}>
        <h3 style={{ marginBottom: '16px', color: '#2d3748' }}>
          Filings by Year
        </h3>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: '8px',
            height: '120px'
          }}
        >
          {(stats.by_year || []).map((row, i) => {
            const pct = Math.round((row.count / maxYearCount) * 100);
            return (
              <div key={i} style={{ textAlign: 'center', flex: '1' }}>
                <div
                  style={{
                    fontSize: '11px',
                    marginBottom: '4px',
                    color: '#555'
                  }}
                >
                  {row.count.toLocaleString()}
                </div>
                <div
                  style={{
                    background: '#667eea',
                    borderRadius: '4px 4px 0 0',
                    height: `${Math.max(pct, 2)}px`,
                    minHeight: '4px'
                  }}
                />
                <div
                  style={{ fontSize: '11px', marginTop: '4px', color: '#333' }}
                >
                  {row.year}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Case Status Breakdown */}
      <div style={card}>
        <h3 style={{ marginBottom: '12px', color: '#2d3748' }}>
          Case Status Breakdown
        </h3>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Status</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Count</th>
            </tr>
          </thead>
          <tbody>
            {(stats.by_status || []).map((row, i) => (
              <tr
                key={i}
                style={{ background: i % 2 === 0 ? '#fff' : '#f7fafc' }}
              >
                <td style={tdStyle}>{row.case_status}</td>
                <td
                  style={{ ...tdStyle, textAlign: 'right', fontWeight: '600' }}
                >
                  {row.count.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default CaseStatsDashboard;
