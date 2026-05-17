import { AlertTriangle, Maximize2, Zap } from 'lucide-react';

const RADAR_IMG =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuB4rwoDfGI6_jMp-NPOKS9mwJ4vLBacA3G0jjMmgygSgzuKDLiERh31C7t_-ybXiLRXMRK6LfJqfNAe9ZWhuNTITvERQOIZtCrGiog8Dk05eANPeuBjXwFCNqpTFCYK0pSqUl09Hbd1KnAY6PsItiI7gHN7hLivJvxaC-TfWf58DVf1EM27eU92XwFuA2Xz5kvce148aEZ44AFXGzJ9MWv6-pVgerUkL5EoMaJSVKtTHHYJyDCc9lzvhGNwK8CTUs8mEdDQDcs00cV0';

const MAP_IMG =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuALyvVXOH5hbam5xLtISmmRlbxJvivIhDpw4Layme53PwuCjOkHUDLjJC5x8yc6h7k4UGqeGiej-3vy00E770wo411O5wKB05oofnnR8hjXg57VfcjYuMbdZb0UmWBczcQOM5mN2vdWSzp25355zci_I8UjNiPT0Z3Uz1e_8gZ15Q_d-T55OKXRrg23MAvV6miqqUGOBL7a5za8gLyLTktqICOBRNjvCSGHotTHhVYYMXzg933mHapmBcD0rV1DUuALH_EM1jmnUT7_';

const INTEL_WIDGETS = [
  { label: 'Targeting Accuracy', value: '100% Precision', bar: 100, accent: 'cyan' },
  { label: 'Predictive Recall', value: '95% Accuracy', sub: '4 Hours Pre-Event', accent: 'cyan' },
  { label: 'Strategic Forecast', value: '73% Accuracy', sub: '1 Year Advance Prediction', accent: 'amber' },
  { label: 'Tactical Accuracy', value: '80% Accuracy', sub: 'Day of Event Validation', accent: 'cyan' },
];

const LIVE_FEED = [
  {
    time: '14:22:04',
    type: 'update',
    text: 'PREDICTION_UPDATE: Sector 4-Beta probability increased to 92%. Confirming assets.',
  },
  {
    time: '14:21:45',
    type: 'strike',
    text: 'STRIKE_CONFIRMED: Event detected in Moore Cluster. Redirecting engine resources.',
  },
  {
    time: '14:20:12',
    type: 'update',
    text: 'Certainty threshold met for #LEAD-8845. Notification sent to field units.',
  },
  {
    time: '14:18:55',
    type: 'update',
    text: 'Atmospheric pressure drop detected. Engine scaling compute in Oklahoma City grid.',
  },
];

const OUTREACH_LEADS = [
  { name: 'Prestige Estates', count: '42 High-Value Properties', badge: 'Critical', cls: 'error' },
  { name: 'Corporate Corridor', count: '12 Commercial Complexes', badge: 'Priority', cls: 'cyan' },
  { name: 'Lakeside Manor', count: '85 Residential Units', badge: 'Standard', cls: 'dim' },
];

export default function StormDashboard({ onBrowseLeads }) {
  return (
    <div className="storm-db fade-in">
      {/* Background map */}
      <div className="storm-db-mapbg" aria-hidden>
        <img src={MAP_IMG} alt="" className="storm-db-mapimg" />
        <div className="storm-db-mapoverlay" />
      </div>

      <div className="storm-db-content">
        {/* Headline */}
        <header className="storm-db-headline">
          <h1 className="storm-db-title">
            World&apos;s Most Advanced
            <br />
            <span className="storm-db-title-accent">Probabilistic Storm Engine.</span>
          </h1>
          <p className="storm-db-subtitle">
            <span className="storm-db-line" aria-hidden />
            Targeting where revenue will strike.
          </p>
        </header>

        {/* 3-column dashboard grid */}
        <div className="storm-db-grid">
          {/* Left: intel widgets */}
          <div className="storm-db-widgets">
            {INTEL_WIDGETS.map((w) => (
              <div key={w.label} className={`storm-widget glass storm-widget--${w.accent}`}>
                <span className="storm-widget-label">{w.label}</span>
                <div className="storm-widget-value">{w.value}</div>
                {w.sub && <span className="storm-widget-sub muted">{w.sub}</span>}
                {w.bar != null && (
                  <div className="storm-widget-bar">
                    <div className="storm-widget-bar-fill" style={{ width: `${w.bar}%` }} />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Center: radar visualizer */}
          <div className="storm-db-center">
            <div className="storm-visualizer glass">
              <div className="storm-vis-header">
                <div className="storm-vis-title">
                  <AlertTriangle size={18} className="storm-vis-alert" aria-hidden />
                  Intelligence Visualizer
                </div>
                <span className="storm-badge-critical">ACTIVE THREAT</span>
              </div>

              <div className="storm-vis-grid">
                <div className="storm-vis-radar">
                  <img src={RADAR_IMG} alt="Radar scan — Dallas-Fort Worth hail cell #H-9942" />
                  <div className="storm-vis-radar-overlay" aria-hidden />
                  <div className="storm-vis-radar-footer">
                    <div>
                      <p className="storm-vis-cell">CELL ID: #H-9942</p>
                      <p className="storm-vis-loc muted">Dallas-Fort Worth Metroplex</p>
                    </div>
                    <Maximize2 size={15} aria-hidden />
                  </div>
                </div>

                <div className="storm-vis-stats">
                  <div className="storm-stat-card">
                    <p className="storm-stat-label">Max Hail Size</p>
                    <p className="storm-stat-val storm-stat-val--error">2.75&quot;</p>
                  </div>
                  <div className="storm-stat-card">
                    <p className="storm-stat-label">Impacted Parcels</p>
                    <p className="storm-stat-val">6,400</p>
                  </div>
                  <div className="storm-stat-card storm-stat-card--accent">
                    <p className="storm-stat-label">Est. Opportunity</p>
                    <p className="storm-stat-val">$4.2M</p>
                  </div>
                </div>
              </div>

              <div className="storm-vis-footer">
                <span className="muted small">Data fresh as of 2 mins ago</span>
                <button type="button" className="cta-btn-primary sm" onClick={onBrowseLeads}>
                  Export Lead Batch
                </button>
              </div>
            </div>
          </div>

          {/* Right: outreach wizard + live feed */}
          <div className="storm-db-right">
            <div className="storm-outreach glass">
              <div className="storm-outreach-header">
                <Zap size={15} aria-hidden /> Tactical Outreach Wizard
              </div>
              <div className="storm-outreach-meta">
                <span className="muted small">Pre-Storm Lead List</span>
                <span className="storm-outreach-time">T-minus 48h</span>
              </div>
              <div className="storm-outreach-leads">
                {OUTREACH_LEADS.map((lead) => (
                  <div key={lead.name} className="storm-lead-item">
                    <div className="storm-lead-row">
                      <span className="storm-lead-name">{lead.name}</span>
                      <span className={`storm-lead-badge storm-lead-badge--${lead.cls}`}>{lead.badge}</span>
                    </div>
                    <div className="storm-lead-count muted small">{lead.count}</div>
                  </div>
                ))}
              </div>
              <button type="button" className="cta-btn-primary storm-deploy-btn" onClick={onBrowseLeads}>
                Deploy Teams Now
              </button>
            </div>

            <div className="storm-livefeed glass">
              <div className="storm-livefeed-header">
                <span className="storm-livefeed-dot" aria-hidden /> Live Intelligence
                <span className="storm-livefeed-tag muted small">SECURED_LINE_ALPHA</span>
              </div>
              <div className="storm-livefeed-list">
                {LIVE_FEED.map((item) => (
                  <div key={item.time} className={`storm-feed-item storm-feed-item--${item.type}`}>
                    <span className="storm-feed-time muted small">{item.time}</span>
                    <p className="storm-feed-text small">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="storm-statusbar" aria-label="System status">
        <div className="storm-status-left">
          <span className="pulse" aria-hidden /> System Online
          <span className="storm-status-sep" aria-hidden>·</span>
          <span className="muted">Sat: Active</span>
          <span className="storm-status-sep" aria-hidden>·</span>
          <span className="muted">Latency: 12ms</span>
        </div>
        <div className="muted small">STORM_ENGINE_V4.2.0 // REVENUE_TARGETING_ACTIVE</div>
      </div>
    </div>
  );
}
