import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import Papa from 'papaparse';
import { Map as MapIcon, List, RefreshCw, Crosshair, ExternalLink, Sparkles } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

const SPC_TODAY =
  'https://www.spc.noaa.gov/climo/reports/today_filtered_hail.csv';
const SPC_YESTERDAY =
  'https://www.spc.noaa.gov/climo/reports/yesterday_filtered_hail.csv';

function inchesFromSize(raw) {
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return n / 100;
}

function markerColor(inches) {
  if (inches >= 2) return '#f43f5e';
  if (inches >= 1.75) return '#fb923c';
  if (inches >= 1.5) return '#fbbf24';
  return '#38bdf8';
}

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const b = L.latLngBounds(points.map((p) => [p.lat, p.lon]));
    if (b.isValid()) map.fitBounds(b, { padding: [48, 48], maxZoom: 9, animate: false });
  }, [map, points]);
  return null;
}

async function fetchSpcHailRows() {
  const out = [];
  for (const url of [SPC_TODAY, SPC_YESTERDAY]) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) continue;
      const text = await res.text();
      const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
      const label = url.includes('today') ? 'today' : 'yesterday';
      for (const row of parsed.data) {
        if (!row || !row.Lat) continue;
        const lat = parseFloat(row.Lat);
        const lon = parseFloat(row.Lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
        const inches = inchesFromSize(row.Size);
        out.push({
          key: `${label}-${row.Time}-${row.Lat}-${row.Lon}-${row.Size}`,
          label,
          timeUtc: String(row.Time || '').trim(),
          inches,
          location: String(row.Location || '').trim(),
          county: String(row.County || '').trim(),
          state: String(row.State || '').trim(),
          lat,
          lon,
          comments: String(row.Comments || '').trim().slice(0, 280),
        });
      }
    } catch {
      /* ignore */
    }
  }
  return out;
}

export default function HstrikeMap({
  minInches = 1.5,
  onFocusState,
  onScrollToLeads,
}) {
  const [mounted, setMounted] = useState(false);
  const [mode, setMode] = useState('map');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const raw = await fetchSpcHailRows();
      setRows(raw);
    } catch (e) {
      setError(e.message || 'Could not load SPC data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const major = useMemo(
    () => rows.filter((r) => r.inches >= minInches).sort((a, b) => b.inches - a.inches),
    [rows, minInches],
  );

  const center = useMemo(() => {
    if (!major.length) return [39.5, -98.35];
    const lat = major.reduce((s, p) => s + p.lat, 0) / major.length;
    const lon = major.reduce((s, p) => s + p.lon, 0) / major.length;
    return [lat, lon];
  }, [major]);

  if (!mounted) {
    return (
      <section className="hstrike-section glass-inset" aria-label="Hail activity map loading">
        <div className="hstrike-skeleton">Loading map…</div>
      </section>
    );
  }

  return (
    <section className="hstrike-section glass-inset" id="live-hail-map" aria-labelledby="hstrike-heading">
      <div className="hstrike-head">
        <div>
          <h3 id="hstrike-heading" className="hstrike-title">
            <Crosshair size={20} className="hstrike-title-ic" aria-hidden />
            Live major hail — NOAA Storm Prediction Center
          </h3>
          <p className="muted small hstrike-sub">
            Filtered LSR hail for <strong>today &amp; yesterday</strong> (≥{minInches}&quot;). Hover pins for details.
            Same public feeds we ingest in{' '}
            <code className="inline-code">live_hail_ingest.py</code>. Reports are preliminary.
          </p>
        </div>
        <div className="hstrike-actions">
          <div className="hstrike-toggle" role="group" aria-label="View mode">
            <button
              type="button"
              className={mode === 'map' ? 'active' : ''}
              onClick={() => setMode('map')}
            >
              <MapIcon size={16} /> Map
            </button>
            <button
              type="button"
              className={mode === 'list' ? 'active' : ''}
              onClick={() => setMode('list')}
            >
              <List size={16} /> List
            </button>
          </div>
          <button type="button" className="hstrike-refresh" onClick={load} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <a
            href={SPC_TODAY}
            target="_blank"
            rel="noopener noreferrer"
            className="hstrike-outlink"
          >
            Raw CSV <ExternalLink size={14} />
          </a>
        </div>
      </div>

      {error && <p className="hstrike-error">{error}</p>}

      {mode === 'map' && (
        <div className="hstrike-map-wrap">
          {loading && !major.length ? (
            <div className="hstrike-skeleton">Pulling SPC CSV…</div>
          ) : major.length === 0 ? (
            <div className="hstrike-empty">
              <p>No qualifying hail reports in the last ~24h window at ≥{minInches}&quot;. Check tomorrow or lower the threshold in code.</p>
              <button type="button" className="cta-btn-secondary" onClick={onScrollToLeads}>
                <Sparkles size={16} /> Browse verified property leads
              </button>
            </div>
          ) : (
            <MapContainer
              center={center}
              zoom={4}
              className="hstrike-leaflet"
              scrollWheelZoom
              worldCopyJump
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />
              <FitBounds points={major} />
              {major.map((p) => (
                <CircleMarker
                  key={p.key}
                  center={[p.lat, p.lon]}
                  radius={6 + Math.min(10, p.inches * 2)}
                  pathOptions={{
                    color: '#0f172a',
                    weight: 1,
                    fillColor: markerColor(p.inches),
                    fillOpacity: 0.85,
                  }}
                >
                  <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                    <div className="hstrike-tip">
                      <strong>
                        {p.inches.toFixed(2)}&quot; hail · {p.location}, {p.state}
                      </strong>
                      <br />
                      <span className="tip-muted">
                        {p.county} Co. · {p.timeUtc} UTC ({p.label})
                      </span>
                      {p.comments && (
                        <>
                          <br />
                          <span className="tip-comments">{p.comments}</span>
                        </>
                      )}
                    </div>
                  </Tooltip>
                </CircleMarker>
              ))}
            </MapContainer>
          )}
        </div>
      )}

      {mode === 'list' && (
        <div className="hstrike-list-wrap">
          {loading && !major.length ? (
            <p className="muted small">Loading…</p>
          ) : (
            <ul className="hstrike-list">
              {major.slice(0, 120).map((p) => (
                <li key={p.key}>
                  <div className="hstrike-li-main">
                    <span className="hstrike-li-size">{p.inches.toFixed(2)}&quot;</span>
                    <span>
                      {p.location}, {p.state} · {p.county}
                    </span>
                    <span className="muted small">
                      {p.timeUtc} UTC · {p.label}
                    </span>
                  </div>
                  <div className="hstrike-li-actions">
                    {onFocusState && p.state && (
                      <button
                        type="button"
                        className="linkish"
                        onClick={() => onFocusState(p.state)}
                      >
                        Match leads in {p.state}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="hstrike-cta">
        <p>
          <strong>Ridgeline-only access:</strong> pair these strikes with forensic tiles and call-ready contacts — before the
          homeowner knows they need you. Every storm is a chance to help your community <em>and</em> grow revenue.
        </p>
        <button type="button" className="cta-btn-primary" onClick={onScrollToLeads}>
          Open marketplace — claim ZIPs first
        </button>
      </div>
    </section>
  );
}
