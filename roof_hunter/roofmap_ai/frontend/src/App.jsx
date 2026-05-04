import { useCallback, useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const b = L.latLngBounds(points.map((p) => [p.lat, p.lng]));
    if (b.isValid()) map.fitBounds(b, { padding: [40, 40], maxZoom: 14 });
  }, [map, points]);
  return null;
}

function scoreColor(score) {
  if (score >= 0.75) return '#f85149';
  if (score >= 0.5) return '#d29922';
  return '#3fb950';
}

export default function App() {
  const [leads, setLeads] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [address, setAddress] = useState('123 Main St, Oklahoma City, OK');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const refreshLeads = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API}/leads/map`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setLeads(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message || 'Failed to load leads');
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshLeads();
  }, [refreshLeads]);

  const points = useMemo(() => leads.map((l) => ({ lat: l.lat, lng: l.lng })), [leads]);
  const center = useMemo(() => {
    if (!points.length) return [39.5, -98.35];
    const lat = points.reduce((s, p) => s + p.lat, 0) / points.length;
    const lng = points.reduce((s, p) => s + p.lng, 0) / points.length;
    return [lat, lng];
  }, [points]);

  const ingestNo = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API}/ingest/noaa/hail-snapshot`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      await refreshLeads();
    } catch (e) {
      setError(e.message || 'NOAA ingest failed');
    } finally {
      setBusy(false);
    }
  };

  const saveProperty = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API}/property`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, save: true, name: 'Imported lead' }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      await refreshLeads();
      setSelected({
        id: data.lead_id,
        address: data.address,
        name: 'Imported lead',
        lat: data.lat,
        lng: data.lng,
        damage_index: data.damage_index,
        lead_score: data.lead_score,
        image_url: null,
        script_type: null,
        priority: null,
        created_at: new Date().toISOString(),
      });
    } catch (e) {
      setError(e.message || 'Save failed');
    } finally {
      setBusy(false);
    }
  };

  if (!mounted) return <div className="muted" style={{ padding: 24 }}>Loading map…</div>;

  return (
    <div className="app-shell">
      <div className="map-pane">
        <MapContainer center={center} zoom={4} className="leaflet-map" scrollWheelZoom>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          {points.length > 0 && <FitBounds points={points} />}
          {leads.map((lead) => (
            <CircleMarker
              key={lead.id}
              center={[lead.lat, lead.lng]}
              radius={8 + lead.lead_score * 14}
              pathOptions={{
                color: '#0d1117',
                weight: 2,
                fillColor: scoreColor(lead.lead_score),
                fillOpacity: 0.9,
              }}
              eventHandlers={{
                click: () => setSelected(lead),
              }}
            >
              <Popup>
                <strong>{lead.name || 'Lead'}</strong>
                <br />
                {lead.address}
                <br />
                <span style={{ color: '#333' }}>Score {lead.lead_score}</span>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <aside className="side-panel">
        <h1>Ridgeline AI · RoofMap</h1>
        <p className="muted">Nearmap-style explorer — hail context + CV stub (YOLO-ready).</p>

        {error && <div className="error-banner">{error}</div>}

        <div className="toolbar">
          <button type="button" className="primary" disabled={busy} onClick={refreshLeads}>
            Refresh leads
          </button>
          <button type="button" disabled={busy} onClick={ingestNo}>
            NOAA hail snapshot
          </button>
          <a href={`${API}/export/csv`} target="_blank" rel="noreferrer">
            <button type="button">Export CSV</button>
          </a>
        </div>

        <h2>Add property (saved to Postgres)</h2>
        <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Address" />
        <div className="toolbar" style={{ marginTop: 8 }}>
          <button type="button" className="primary" disabled={busy} onClick={saveProperty}>
            Geocode + score + save
          </button>
        </div>

        <h2>Selected property</h2>
        {loading && <p className="muted">Loading…</p>}
        {!loading && !selected && <p className="muted">Click a marker or save a new property.</p>}
        {selected && (
          <div className="stat-grid">
            <div className="stat-card">
              <span className="muted">Lead score (0–1)</span>
              <strong>{selected.lead_score}</strong>
            </div>
            <div className="stat-card">
              <span className="muted">Damage index</span>
              <strong>{selected.damage_index}</strong>
            </div>
            <div className="stat-card" style={{ gridColumn: '1 / -1' }}>
              <span className="muted">Address</span>
              <strong style={{ fontSize: '0.95rem', fontWeight: 600 }}>{selected.address}</strong>
            </div>
            {selected.script_type && (
              <div className="stat-card">
                <span className="muted">Script</span>
                <strong style={{ fontSize: '0.9rem' }}>{selected.script_type}</strong>
              </div>
            )}
            {selected.priority && (
              <div className="stat-card">
                <span className="muted">Priority</span>
                <strong style={{ fontSize: '0.9rem' }}>{selected.priority}</strong>
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
