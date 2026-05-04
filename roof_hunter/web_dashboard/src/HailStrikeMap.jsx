import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet';
import L from 'leaflet';
import Papa from 'papaparse';
import { Map as MapIcon, List, RefreshCw, Crosshair, ExternalLink, Sparkles } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

const SPC_TODAY =
  'https://www.spc.noaa.gov/climo/reports/today_filtered_hail.csv';
const SPC_YESTERDAY =
  'https://www.spc.noaa.gov/climo/reports/yesterday_filtered_hail.csv';

/** Refresh “live” SPC day files on this interval (archive is loaded once). */
const LIVE_REFRESH_MS = 15 * 60 * 1000;

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
    if (b.isValid()) map.fitBounds(b, { padding: [48, 48], maxZoom: 8, animate: false });
  }, [map, points]);
  return null;
}

function parseSpcHailCsv(text, label, daysAgo) {
  const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
  const out = [];
  for (const row of parsed.data) {
    if (!row || !row.Lat) continue;
    const lat = parseFloat(row.Lat);
    const lon = parseFloat(row.Lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const inches = inchesFromSize(row.Size);
    out.push({
      key: `${label}-${row.Time}-${row.Lat}-${row.Lon}-${row.Size}`,
      label,
      daysAgo,
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
  return out;
}

async function fetchSpcHailRows() {
  const out = [];
  const jobs = [
    [SPC_TODAY, 'today', 0],
    [SPC_YESTERDAY, 'yesterday', 1],
  ];
  for (const [url, label, daysAgo] of jobs) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) continue;
      const text = await res.text();
      out.push(...parseSpcHailCsv(text, label, daysAgo));
    } catch {
      /* ignore */
    }
  }
  return out;
}

/**
 * Historical filtered hail CSVs — same public pattern as `live_hail_ingest.py` (SPC_ARCHIVE_HAIL).
 * Range: day offsets `startDaysAgo` … `maxDaysAgo` (inclusive), UTC calendar roll.
 */
async function fetchSpcArchiveHailRange(
  maxDaysAgo = 364,
  startDaysAgo = 2,
  concurrency = 6,
  onProgress,
) {
  const anchor = new Date();
  const utc = new Date(Date.UTC(anchor.getUTCFullYear(), anchor.getUTCMonth(), anchor.getUTCDate()));
  const dates = [];
  for (let i = startDaysAgo; i <= maxDaysAgo; i++) {
    const d = new Date(utc);
    d.setUTCDate(d.getUTCDate() - i);
    const yy = String(d.getUTCFullYear() % 100).padStart(2, '0');
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(d.getUTCDate()).padStart(2, '0');
    dates.push({ ds: `${yy}${mm}${dd}`, daysAgo: i });
  }

  const out = [];
  let completed = 0;
  for (let i = 0; i < dates.length; i += concurrency) {
    const batch = dates.slice(i, i + concurrency);
    const batchRows = await Promise.all(
      batch.map(async ({ ds, daysAgo }) => {
        const url = `https://www.spc.noaa.gov/climo/reports/${ds}_rpts_filtered_hail.csv`;
        try {
          const res = await fetch(url, { cache: 'no-store' });
          if (!res.ok) return [];
          const text = await res.text();
          return parseSpcHailCsv(text, `archive-${ds}`, daysAgo);
        } catch {
          return [];
        }
      }),
    );
    for (const chunk of batchRows) out.push(...chunk);
    completed += batch.length;
    onProgress?.(completed, dates.length);
  }
  return out;
}

/** Keep one row per approximate strike; prefer the most recent SPC file it appeared in. */
function mergePreferRecent(rows) {
  const m = new Map();
  for (const r of rows) {
    const k = `${r.lat.toFixed(4)}|${r.lon.toFixed(4)}|${r.timeUtc}|${r.inches.toFixed(2)}|${r.state}`;
    const ex = m.get(k);
    if (!ex || r.daysAgo < ex.daysAgo) m.set(k, r);
  }
  return [...m.values()];
}

export default function HailStrikeMap({
  minInches = 2,
  maxMapMarkers = 1500,
  listLimit = 400,
  onFocusState,
  onScrollToLeads,
}) {
  const [mode, setMode] = useState('map');
  const [rows, setRows] = useState([]);
  const [loadingLive, setLoadingLive] = useState(true);
  const [loadingArchive, setLoadingArchive] = useState(true);
  const [archiveProgress, setArchiveProgress] = useState(null);
  const [error, setError] = useState(null);
  const [lastLiveRefresh, setLastLiveRefresh] = useState(null);
  const archiveStarted = useRef(false);

  const applyLiveRows = useCallback((liveRows) => {
    setRows((prev) => {
      const archived = prev.filter((r) => String(r.label).startsWith('archive-'));
      return mergePreferRecent([...liveRows, ...archived]);
    });
    setLastLiveRefresh(new Date());
  }, []);

  const loadLive = useCallback(async () => {
    setLoadingLive(true);
    setError(null);
    try {
      const liveRows = await fetchSpcHailRows();
      applyLiveRows(liveRows);
    } catch (e) {
      setError(e.message || 'Could not load SPC data');
    } finally {
      setLoadingLive(false);
    }
  }, [applyLiveRows]);

  const loadArchive = useCallback(async () => {
    if (archiveStarted.current) return;
    archiveStarted.current = true;
    setLoadingArchive(true);
    setArchiveProgress({ done: 0, total: 363 });
    try {
      const historical = await fetchSpcArchiveHailRange(364, 2, 6, (done, total) => {
        setArchiveProgress({ done, total });
      });
      setRows((prev) => mergePreferRecent([...prev, ...historical]));
    } catch {
      /* non-fatal: map still shows recent */
    } finally {
      setArchiveProgress(null);
      setLoadingArchive(false);
    }
  }, []);

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- initial SPC load */
    loadLive();
    loadArchive();
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [loadLive, loadArchive]);

  useEffect(() => {
    const t = setInterval(() => {
      loadLive();
    }, LIVE_REFRESH_MS);
    return () => clearInterval(t);
  }, [loadLive]);

  const major = useMemo(
    () => rows.filter((r) => r.inches >= minInches).sort((a, b) => a.daysAgo - b.daysAgo || b.inches - a.inches),
    [rows, minInches],
  );

  const mapMarkers = useMemo(() => major.slice(0, maxMapMarkers), [major, maxMapMarkers]);

  const center = useMemo(() => {
    if (!mapMarkers.length) return [39.5, -98.35];
    const lat = mapMarkers.reduce((s, p) => s + p.lat, 0) / mapMarkers.length;
    const lon = mapMarkers.reduce((s, p) => s + p.lon, 0) / mapMarkers.length;
    return [lat, lon];
  }, [mapMarkers]);

  const showMapSpinner = loadingLive && !mapMarkers.length;
  const awaitingYearData = loadingArchive && major.length === 0 && !loadingLive;
  const archiveBanner =
    archiveProgress &&
    archiveProgress.total > 0 &&
    `Loading NOAA/SPC archive (rolling year)… ${archiveProgress.done}/${archiveProgress.total} days`;

  return (
    <section className="hstrike-section glass-inset" id="live-hail-map" aria-labelledby="hstrike-heading">
      <div className="hstrike-head">
        <div>
          <h3 id="hstrike-heading" className="hstrike-title">
            <Crosshair size={20} className="hstrike-title-ic" aria-hidden />
            USA hail ≥2″ — NOAA Storm Prediction Center
          </h3>
          <p className="muted small hstrike-sub">
            <strong>Nationwide</strong> filtered LSR hail for the <strong>last ~365 days</strong> (≥{minInches}
            &Prime;), plus <strong>today &amp; yesterday</strong> refreshed automatically every 15 minutes from the
            same public CSV feeds the pipeline ingests (
            <code className="inline-code">live_hail_ingest.py</code>). Reports are preliminary; times are UTC.
          </p>
          {(archiveBanner || lastLiveRefresh) && (
            <p className="muted small hstrike-sub" style={{ marginTop: '0.35rem' }}>
              {archiveBanner && <span>{archiveBanner}. </span>}
              {lastLiveRefresh && (
                <span>Live day files last checked: {lastLiveRefresh.toLocaleString()}.</span>
              )}
            </p>
          )}
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
          <button
            type="button"
            className="hstrike-refresh"
            onClick={() => {
              loadLive();
            }}
            disabled={loadingLive}
          >
            <RefreshCw size={16} className={loadingLive ? 'spin' : ''} /> Refresh live
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

      {major.length > mapMarkers.length && (
        <p className="muted small" style={{ margin: '0 0 0.75rem' }}>
          Showing {mapMarkers.length} of {major.length} pins on the map (most recent &amp; largest first) for
          performance. Full set appears in the list view (capped at {listLimit}).
        </p>
      )}

      {mode === 'map' && (
        <div className="hstrike-map-wrap">
          {showMapSpinner || awaitingYearData ? (
            <div className="hstrike-skeleton">
              {awaitingYearData
                ? 'Loading NOAA/SPC filtered hail archive (rolling year, ≥2″)…'
                : 'Pulling SPC today/yesterday CSV…'}
            </div>
          ) : mapMarkers.length === 0 ? (
            <div className="hstrike-empty">
              <p>
                No qualifying hail reports at ≥{minInches}&Prime; in the last ~365 days in this merge. Try again after
                convective weather, or confirm SPC feeds are reachable.
              </p>
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
              <FitBounds points={mapMarkers} />
              {mapMarkers.map((p) => (
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
                        {p.inches.toFixed(2)}&Prime; hail · {p.location}, {p.state}
                      </strong>
                      <br />
                      <span className="tip-muted">
                        {p.county} Co. · {p.timeUtc} UTC · {p.label} · ~{p.daysAgo}d ago
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
          {loadingLive && !major.length ? (
            <p className="muted small">Loading…</p>
          ) : (
            <ul className="hstrike-list">
              {major.slice(0, listLimit).map((p) => (
                <li key={p.key}>
                  <div className="hstrike-li-main">
                    <span className="hstrike-li-size">{p.inches.toFixed(2)}&Prime;</span>
                    <span>
                      {p.location}, {p.state} · {p.county}
                    </span>
                    <span className="muted small">
                      {p.timeUtc} UTC · {p.label} · ~{p.daysAgo}d ago
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
          {loadingArchive && (
            <p className="muted small" style={{ marginTop: '0.75rem' }}>
              Still merging historical SPC files… list will fill in.
            </p>
          )}
        </div>
      )}

      <div className="hstrike-cta">
        <p>
          <strong>Ridgeline-only access:</strong> pair government hail reports with forensic tiles and call-ready
          contacts in <strong>any state</strong> we cover — not just one corridor.
        </p>
        <button type="button" className="cta-btn-primary" onClick={onScrollToLeads}>
          Open marketplace — claim ZIPs first
        </button>
      </div>
    </section>
  );
}
