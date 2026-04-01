import React, { useState, useEffect } from 'react';

var STATUS_API = '/api/v1/admin/status';
var HEALTH_API = '/api/v1/admin/spider-health';

function fmt(n) {
  return (n != null ? n : 0).toLocaleString();
}
function pct(a, b) {
  return b ? Math.min(100, (a / b) * 100).toFixed(1) : '0.0';
}

function SectionLabel({ title }) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 700,
        color: '#aaa',
        letterSpacing: 1.2,
        textTransform: 'uppercase',
        marginBottom: 10,
        marginTop: 22
      }}
    >
      {title}
    </div>
  );
}

function StatCard({ label, value, color, sub }) {
  return (
    <div
      style={{
        background: '#fff',
        borderRadius: 10,
        padding: '16px 20px',
        boxShadow: '0 1px 6px rgba(0,0,0,.07)',
        flex: 1,
        minWidth: 100
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: '#aaa',
          fontWeight: 600,
          letterSpacing: 0.8,
          textTransform: 'uppercase',
          marginBottom: 6
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 26,
          fontWeight: 700,
          color: color || '#222',
          lineHeight: 1.1
        }}
      >
        {value != null ? value : '—'}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>{sub}</div>
      )}
    </div>
  );
}

function QueueCard({ label, value, color, sub }) {
  return (
    <div
      style={{
        background: '#fff',
        borderRadius: 10,
        padding: '16px 20px',
        boxShadow: '0 1px 6px rgba(0,0,0,.07)',
        flex: 1,
        minWidth: 100
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: '#aaa',
          fontWeight: 600,
          letterSpacing: 0.8,
          textTransform: 'uppercase',
          marginBottom: 6
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || '#222' }}>
        {value != null ? fmt(value) : '—'}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>{sub}</div>
      )}
    </div>
  );
}

function Bar({ label, val, total, color, sublabel }) {
  var p = total ? Math.min(100, (val / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: 5,
          gap: 8
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: '#444' }}>
          {label}
        </span>
        <span
          style={{
            background: color,
            color: '#fff',
            fontSize: 11,
            fontWeight: 700,
            borderRadius: 10,
            padding: '1px 8px'
          }}
        >
          {p.toFixed(1)}%
        </span>
      </div>
      <div style={{ background: '#eee', borderRadius: 6, height: 8 }}>
        <div
          style={{
            width: p + '%',
            height: 8,
            borderRadius: 6,
            background: color,
            transition: 'width .5s'
          }}
        />
      </div>
      <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>
        {sublabel || fmt(val) + ' of ' + fmt(total)}
      </div>
    </div>
  );
}

export default function Admin() {
  var [status, setStatus] = useState(null);
  var [health, setHealth] = useState(null);
  var [restarting, setRestarting] = useState(false);

  function fetchAll() {
    fetch(STATUS_API)
      .then(function(r) {
        return r.json();
      })
      .then(setStatus)
      .catch(function() {});
    fetch(HEALTH_API)
      .then(function(r) {
        return r.json();
      })
      .then(setHealth)
      .catch(function() {});
  }

  useEffect(function() {
    fetchAll();
    var t = setInterval(fetchAll, 3000);
    return function() {
      clearInterval(t);
    };
  }, []);

  function restartSpiders() {
    setRestarting(true);
    fetch('/api/v1/admin/restart-spider', { method: 'POST' })
      .then(function() {
        setTimeout(function() {
          setRestarting(false);
        }, 3000);
      })
      .catch(function() {
        setRestarting(false);
      });
  }

  var db = status && status.db ? status.db : {};
  var queues = status && status.queues ? status.queues : {};
  var disk = status && status.disk ? status.disk : null;
  var fcSp = status && status.fc_spider ? status.fc_spider : {};

  var dd = health && health.datadome_2min != null ? health.datadome_2min : null;
  var ddColor =
    dd == null ? '#ccc' : dd > 50 ? '#e74c3c' : dd > 10 ? '#f39c12' : '#2ecc71';

  var scrapeRate = db.scraped_last_1h || 0;
  var diskSub = disk
    ? disk.used_gb +
      ' GB used · ' +
      disk.free_gb +
      ' GB free of ' +
      disk.total_gb +
      ' GB'
    : null;

  return (
    <div
      style={{
        padding: '24px 32px',
        fontFamily: 'Segoe UI, sans-serif',
        maxWidth: 1100,
        background: '#f7f8fa',
        minHeight: '100vh'
      }}
    >
      {/* ── Top bar ── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          marginBottom: 24,
          background: '#fff',
          borderRadius: 10,
          padding: '12px 20px',
          boxShadow: '0 1px 6px rgba(0,0,0,.07)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: ddColor
            }}
          />
          <div>
            <div
              style={{
                fontSize: 10,
                color: '#aaa',
                textTransform: 'uppercase',
                letterSpacing: 0.8,
                fontWeight: 600
              }}
            >
              DataDome Blocks
            </div>
            <div style={{ fontSize: 13, color: '#555' }}>
              {dd != null ? dd : '—'}{' '}
              <span style={{ color: '#aaa' }}>last 2 min</span>
            </div>
          </div>
        </div>

        <div style={{ width: 1, height: 32, background: '#eee' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: fcSp.running ? '#2ecc71' : '#ccc'
            }}
          />
          <div>
            <div
              style={{
                fontSize: 10,
                color: '#aaa',
                textTransform: 'uppercase',
                letterSpacing: 0.8,
                fontWeight: 600
              }}
            >
              FC Enum Spider
            </div>
            <div style={{ fontSize: 13, color: '#555' }}>
              {fcSp.running ? 'Running' : 'Stopped'}
              {fcSp.current_segment ? ' · ' + fcSp.current_segment : ''}
            </div>
          </div>
        </div>

        <div style={{ marginLeft: 'auto' }}>
          <button
            onClick={restartSpiders}
            disabled={restarting}
            style={{
              background: restarting ? '#aaa' : '#e74c3c',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              padding: '9px 20px',
              fontWeight: 700,
              fontSize: 13,
              cursor: restarting ? 'default' : 'pointer'
            }}
          >
            {restarting ? 'Restarting…' : '🔄 Restart Spiders'}
          </button>
        </div>
      </div>

      {/* ── DATABASE ── */}
      <SectionLabel title="Database" />
      <div
        style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}
      >
        <StatCard label="Total Cases" value={fmt(db.total)} color="#222" />
        <StatCard
          label="Scraped"
          value={fmt(db.scraped)}
          color="#2980b9"
          sub={pct(db.scraped, db.total) + '% of total'}
        />
        <StatCard
          label="Parsed"
          value={fmt(db.parsed)}
          color="#27ae60"
          sub={pct(db.parsed, db.total) + '% of total'}
        />
        <StatCard
          label="FC / ROR 2024+"
          value={fmt(db.foreclosures_scraped)}
          color="#8e44ad"
          sub="foreclosures + redemptions"
        />
        <StatCard
          label="Unscraped"
          value={fmt(db.remaining)}
          color={db.remaining > 0 ? '#e74c3c' : '#27ae60'}
          sub="pending full scrape"
        />
      </div>

      {/* ── FC ENUM SPIDER ── */}
      <SectionLabel title="FC Enum Spider" />
      <div
        style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}
      >
        <StatCard
          label="Cases Found"
          value={fmt(fcSp.found)}
          color="#8e44ad"
          sub="FC + ROR this run"
        />
        <StatCard
          label="Seqs Checked"
          value={fmt(fcSp.checked)}
          color="#555"
          sub="sequences scanned"
        />
        <StatCard
          label="Find Rate"
          value={
            fcSp.rate_per_hour != null
              ? fmt(Math.round(fcSp.rate_per_hour))
              : '—'
          }
          color="#e67e22"
          sub="FC cases / hour"
        />
        <StatCard
          label="Scraper Queue"
          value={fmt(queues.scraper)}
          color="#e67e22"
          sub="waiting for full scrape"
        />
        <StatCard
          label="Scrape Rate"
          value={fmt(scrapeRate)}
          color="#2980b9"
          sub="scraped / hour"
        />
      </div>

      {/* ── ACTIVITY ── */}
      <SectionLabel title="Scraper Activity" />
      <div
        style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}
      >
        <StatCard
          label="Scraped / 24H"
          value={fmt(db.scraped_last_24h)}
          color="#2980b9"
          sub="cases touched today"
        />
        <StatCard
          label="Latest Filing"
          value={db.newest_filing_date || '—'}
          color="#222"
          sub="most recent scraped"
        />
        <StatCard
          label="Parser Queue"
          value={fmt(queues.parser)}
          color="#27ae60"
          sub="waiting for parse"
        />
      </div>

      {/* ── PROGRESS ── */}
      <div
        style={{
          display: 'flex',
          gap: 16,
          alignItems: 'flex-start',
          marginTop: 22
        }}
      >
        <div style={{ flex: 2, minWidth: 0 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: '#aaa',
              letterSpacing: 1.2,
              textTransform: 'uppercase',
              marginBottom: 10
            }}
          >
            Progress
          </div>
          <div
            style={{
              background: '#fff',
              borderRadius: 10,
              padding: '20px 24px',
              boxShadow: '0 1px 6px rgba(0,0,0,.07)'
            }}
          >
            <Bar
              label="Scraped"
              val={db.scraped}
              total={db.total}
              color="#2980b9"
            />
            <Bar
              label="Parsed"
              val={db.parsed}
              total={db.total}
              color="#27ae60"
            />
            {disk && (
              <Bar
                label="Disk Usage"
                val={disk.used_gb}
                total={disk.total_gb}
                color="#e67e22"
                sublabel={diskSub}
              />
            )}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 180 }}>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: '#aaa',
              letterSpacing: 1.2,
              textTransform: 'uppercase',
              marginBottom: 10
            }}
          >
            Queues
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <QueueCard
              label="Scraper Queue"
              value={queues.scraper}
              color="#e67e22"
              sub="cases to download"
            />
            <QueueCard
              label="Parser Queue"
              value={queues.parser}
              color="#27ae60"
              sub="cases to parse"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
