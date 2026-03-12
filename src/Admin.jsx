import React, { useState, useEffect, useRef } from 'react';

var API = '/api/v1/admin';

function fmt(n) { return (n != null ? n : 0).toLocaleString(); }
function pct(a, b) { return b ? ((a / b) * 100).toFixed(1) : '0.0'; }
function safe(obj, key) { return obj && obj[key] != null ? obj[key] : null; }

function StatCard(props) {
  return (
    <div style={{
      background: '#fff', borderRadius: 10, padding: '18px 24px',
      boxShadow: '0 2px 8px rgba(0,0,0,.08)', minWidth: 160, flex: 1
    }}>
      <div style={{ fontSize: 13, color: '#888', marginBottom: 4 }}>{props.label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: props.color || '#222' }}>{fmt(props.value)}</div>
      {props.sub && <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>{props.sub}</div>}
    </div>
  );
}

function ProgressBar(props) {
  var p = props.total ? Math.min(100, (props.value / props.total) * 100) : 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#555', marginBottom: 4 }}>
        <span>{props.label}</span>
        <span>{fmt(props.value)} / {fmt(props.total)} ({p.toFixed(1)}%)</span>
      </div>
      <div style={{ background: '#eee', borderRadius: 4, height: 8 }}>
        <div style={{ width: p + '%', background: props.color, height: 8, borderRadius: 4, transition: 'width .4s' }} />
      </div>
    </div>
  );
}

export default function Admin() {
  var [settings, setSettings]   = useState({ zenrows_key: '', scraperapi_key: '' });
  var [keyInput, setKeyInput]   = useState('');
  var [keySaved, setKeySaved]   = useState(false);
  var [startDate, setStartDate] = useState('');
  var [endDate, setEndDate]     = useState('');
  var [status, setStatus]       = useState(null);
  var [running, setRunning]     = useState(false);
  var [error, setError]         = useState('');

  var logRef  = useRef(null);
  var pollRef = useRef(null);

  useEffect(function() {
    fetchSettings();
    fetchStatus();
  }, []);

  useEffect(function() {
    if (running) {
      pollRef.current = setInterval(fetchStatus, 3000);
    } else {
      clearInterval(pollRef.current);
    }
    return function() { clearInterval(pollRef.current); };
  }, [running]);

  var logs = status && status.pipeline ? (status.pipeline.log || []) : [];

  useEffect(function() {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs.length]);

  function fetchSettings() {
    fetch(API + '/settings')
      .then(function(r) { return r.json(); })
      .then(function(d) { setSettings(d); })
      .catch(function() {});
  }

  function fetchStatus() {
    fetch(API + '/status')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        setStatus(d);
        var p = d && d.pipeline;
        setRunning(p && p.running ? true : false);
      })
      .catch(function() {});
  }

  function saveKey() {
    if (!keyInput.trim()) return;
    fetch(API + '/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zenrows_key: keyInput.trim() })
    })
      .then(function(r) { return r.json(); })
      .then(function() {
        setKeySaved(true);
        setKeyInput('');
        fetchSettings();
        setTimeout(function() { setKeySaved(false); }, 3000);
      });
  }

  function toSlash(d) {
    if (!d) return '';
    var parts = d.split('-');
    return parts[1] + '/' + parts[2] + '/' + parts[0];
  }

  function startPipeline() {
    setError('');
    if (!startDate) { setError('Start date is required.'); return; }
    fetch(API + '/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_date: toSlash(startDate), end_date: toSlash(endDate) })
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.error) setError(d.error);
        else { setRunning(true); fetchStatus(); }
      });
  }

  function stopPipeline() {
    fetch(API + '/stop', { method: 'POST' })
      .then(function() { setRunning(false); fetchStatus(); });
  }

  function setPreset(days) {
    var d = new Date();
    var s = new Date(d - days * 86400000);
    setStartDate(s.toISOString().slice(0, 10));
    setEndDate('');
  }

  var db   = (status && status.db)       ? status.db       : {};
  var pipe = (status && status.pipeline) ? status.pipeline : {};

  function stepColor(step) {
    if (!step) return '#888';
    if (step === 'Complete') return '#27ae60';
    if (step === 'Stopped')  return '#e67e22';
    return '#2980b9';
  }

  var presets = [
    { label: 'Last 7 days',   days: 7   },
    { label: 'Last 30 days',  days: 30  },
    { label: 'Last 90 days',  days: 90  },
    { label: 'Last 6 months', days: 180 },
    { label: 'Last 1 year',   days: 365 },
    { label: 'Last 2 years',  days: 730 },
  ];

  return (
    <div style={{ padding: '30px 40px', fontFamily: 'Segoe UI, sans-serif', maxWidth: 960 }}>

      <h2 style={{ marginTop: 0, marginBottom: 6, fontSize: 22 }}>
        Harvest &amp; Scrape Pipeline
      </h2>
      <p style={{ color: '#666', marginTop: 0, marginBottom: 28, fontSize: 13 }}>
        Spider MJCS for case numbers, scrape full case pages via ZenRows, then parse into structured DB tables.
      </p>

      {/* DB Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 30, flexWrap: 'wrap' }}>
        <StatCard label="Total Cases" value={db.total} />
        <StatCard label="Scraped" value={db.scraped}
          sub={pct(db.scraped, db.total) + '% of total'} color="#2980b9" />
        <StatCard label="Parsed" value={db.parsed}
          sub={pct(db.parsed, db.total) + '% of total'} color="#27ae60" />
        <StatCard label="Foreclosures Scraped" value={db.foreclosures_scraped} color="#8e44ad" />
        <StatCard label="Remaining" value={db.remaining}
          color={db.remaining > 0 ? '#e74c3c' : '#27ae60'} />
      </div>

      {/* Two column layout */}
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>

        {/* LEFT */}
        <div style={{ flex: '0 0 380px' }}>

          {/* API Key */}
          <div style={card}>
            <h3 style={cardTitle}>ZenRows API Key</h3>
            <p style={hint}>
              Current key:{' '}
              <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
                {settings.zenrows_key || '(not set)'}
              </code>
            </p>
            <p style={hint}>
              Create a free account at{' '}
              <a href="https://www.zenrows.com" target="_blank" rel="noreferrer">zenrows.com</a>
              {' '}(1,000 free requests/account). Paste your key below.
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                type="password"
                placeholder="Paste new ZenRows API key..."
                value={keyInput}
                onChange={function(e) { setKeyInput(e.target.value); }}
                onKeyDown={function(e) { if (e.key === 'Enter') saveKey(); }}
                style={inputStyle}
              />
              <button onClick={saveKey} style={btnPrimary}>Save</button>
            </div>
            {keySaved && <p style={{ color: '#27ae60', fontSize: 12, marginTop: 6 }}>Key saved.</p>}
          </div>

          {/* Date Range */}
          <div style={Object.assign({}, card, { marginTop: 20 })}>
            <h3 style={cardTitle}>Date Range to Scrape</h3>
            <p style={hint}>Select the filing-date window to spider, scrape, and parse.</p>

            <label style={labelStyle}>
              Start date <span style={{ color: '#e74c3c' }}>*</span>
            </label>
            <input type="date" value={startDate}
              onChange={function(e) { setStartDate(e.target.value); }}
              style={inputStyle} />

            <label style={Object.assign({}, labelStyle, { marginTop: 12 })}>
              End date <span style={{ color: '#888' }}>(optional, defaults to today)</span>
            </label>
            <input type="date" value={endDate}
              onChange={function(e) { setEndDate(e.target.value); }}
              style={inputStyle} />

            {error && <p style={{ color: '#e74c3c', fontSize: 13, marginTop: 8 }}>{error}</p>}

            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              {!running
                ? <button onClick={startPipeline} style={Object.assign({}, btnPrimary, { flex: 1 })}>
                    Start Pipeline
                  </button>
                : <button onClick={stopPipeline} style={Object.assign({}, btnDanger, { flex: 1 })}>
                    Stop
                  </button>
              }
            </div>

            <p style={{ fontSize: 11, color: '#aaa', marginTop: 10 }}>
              Pipeline: Spider (discover) then Scraper (download via ZenRows) then Parser (extract data)
            </p>
          </div>

          {/* Quick presets */}
          <div style={Object.assign({}, card, { marginTop: 20 })}>
            <h3 style={cardTitle}>Quick Presets</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
              {presets.map(function(p) {
                return (
                  <button key={p.days} style={btnSecondary}
                    onClick={function() { setPreset(p.days); }}>
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ flex: 1, minWidth: 300 }}>

          <div style={card}>
            <h3 style={cardTitle}>
              Pipeline Status
              {running && (
                <span style={{
                  marginLeft: 10, display: 'inline-block',
                  width: 10, height: 10, borderRadius: '50%',
                  background: '#27ae60', animation: 'pulse 1.2s infinite'
                }} />
              )}
            </h3>

            <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
              <div>
                <span style={{ fontSize: 12, color: '#888' }}>Status: </span>
                <span style={{ fontWeight: 600, color: running ? '#27ae60' : '#888' }}>
                  {running ? 'Running' : 'Idle'}
                </span>
              </div>
              <div>
                <span style={{ fontSize: 12, color: '#888' }}>Step: </span>
                <span style={{ fontWeight: 600, color: stepColor(pipe.step) }}>
                  {pipe.step || '\u2014'}
                </span>
              </div>
              {pipe.last_run && (
                <div>
                  <span style={{ fontSize: 12, color: '#888' }}>Last run: </span>
                  <span style={{ fontSize: 12, color: '#555' }}>
                    {new Date(pipe.last_run + 'Z').toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            <ProgressBar label="Scraped" value={db.scraped} total={db.total} color="#2980b9" />
            <ProgressBar label="Parsed"  value={db.parsed}  total={db.total} color="#27ae60" />

            <div ref={logRef} style={{
              background: '#1e1e1e', color: '#d4d4d4', borderRadius: 6,
              padding: '10px 14px', fontSize: 12, fontFamily: 'monospace',
              height: 320, overflowY: 'auto', marginTop: 14,
              whiteSpace: 'pre-wrap', wordBreak: 'break-all'
            }}>
              {logs.length === 0
                ? <span style={{ color: '#666' }}>No output yet. Start the pipeline to see live logs.</span>
                : logs.map(function(l, i) { return <div key={i}>{l}</div>; })
              }
            </div>
            <p style={{ fontSize: 11, color: '#aaa', margin: '6px 0 0' }}>
              Logs refresh every 3 seconds while running.
            </p>
          </div>

          {/* Rotation instructions */}
          <div style={Object.assign({}, card, {
            marginTop: 20, background: '#fffbf0', borderLeft: '4px solid #f39c12'
          })}>
            <h3 style={Object.assign({}, cardTitle, { color: '#b7770d' })}>
              Rotating Free Accounts (to scrape 2 years)
            </h3>
            <ol style={{ paddingLeft: 18, fontSize: 13, color: '#555', lineHeight: 1.8 }}>
              <li>Go to <a href="https://www.zenrows.com" target="_blank" rel="noreferrer">zenrows.com</a> and create a free account (1,000 requests)</li>
              <li>Copy your API key, paste it above, click Save</li>
              <li>Pick a date range and click Start Pipeline</li>
              <li>When the key runs out, create a new ZenRows account</li>
              <li>Paste the new key and continue from where you left off</li>
            </ol>
            <p style={{ fontSize: 12, color: '#888' }}>
              Each free ZenRows account covers ~1,000 cases. 2 years of foreclosure cases may need 5-50 accounts.
            </p>
          </div>
        </div>
      </div>

      <style>{'\
        @keyframes pulse {\
          0%, 100% { opacity: 1; }\
          50% { opacity: 0.3; }\
        }\
      '}</style>
    </div>
  );
}

var card = {
  background: '#fff', borderRadius: 10, padding: '20px 24px',
  boxShadow: '0 2px 8px rgba(0,0,0,.08)'
};
var cardTitle  = { margin: '0 0 12px', fontSize: 15, fontWeight: 600 };
var hint       = { fontSize: 13, color: '#666', margin: '0 0 10px' };
var labelStyle = { display: 'block', fontSize: 13, color: '#555', marginBottom: 4 };
var inputStyle = {
  width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #ddd',
  fontSize: 14, boxSizing: 'border-box', outline: 'none'
};
var btnPrimary = {
  padding: '9px 18px', background: '#2980b9', color: '#fff',
  border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 14
};
var btnDanger = {
  padding: '9px 18px', background: '#e74c3c', color: '#fff',
  border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 14
};
var btnSecondary = {
  padding: '6px 12px', background: '#f0f0f0', color: '#333',
  border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer', fontSize: 12
};
