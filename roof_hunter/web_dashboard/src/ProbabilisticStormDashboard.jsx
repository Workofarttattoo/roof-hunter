import {
  Radar,
  Activity,
  AlertTriangle,
  Layers,
  Database,
  BarChart3,
  Settings,
  Download,
  Maximize2,
  Clock,
  Wind,
  CloudRain
} from 'lucide-react';

export default function ProbabilisticStormDashboard({ onBack }) {
  return (
    <div className="storm-dashboard-container">
      {/* Navigation Sidebar */}
      <nav className="storm-nav">
        <div className="nav-brand">
          <Radar className="brand-icon" />
          <span>STORM_INTEL</span>
        </div>

        <div className="nav-links">
          <div className="nav-group">
            <h3>COMMAND CENTER</h3>
            <button className="nav-item active">
              <Activity size={18} />
              <span>Live Radar</span>
            </button>
            <button className="nav-item">
              <Layers size={18} />
              <span>Tactical Feed</span>
            </button>
            <button className="nav-item">
              <Database size={18} />
              <span>Lead Vault</span>
            </button>
            <button className="nav-item">
              <BarChart3 size={18} />
              <span>Risk Reports</span>
            </button>
            <button className="nav-item">
              <Settings size={18} />
              <span>System Settings</span>
            </button>
          </div>
        </div>

        <button className="generate-leads-btn" onClick={onBack}>
          BROWSE LEADS
        </button>
      </nav>

      {/* Main Content */}
      <main className="storm-main">
        <div className="map-background">
          <div className="map-overlay"></div>

          <div className="visualizer-card glass-premium">
            <div className="card-header">
              <div className="header-title">
                <AlertTriangle className="alert-icon" size={20} />
                <h2>Intelligence Visualizer</h2>
              </div>
              <span className="badge-critical">ACTIVE THREAT</span>
            </div>

            <div className="visualizer-grid">
              <div className="radar-view">
                <div className="radar-img-container">
                  <img
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuB4rwoDfGI6_jMp-NPOKS9mwJ4vLBacA3G0jjMmgygSgzuKDLiERh31C7t_-ybXiLRXMRK6LfJqfNAe9ZWhuNTITvERQOIZtCrGiog8Dk05eANPeuBjXwFCNqpTFCYK0pSqUl09Hbd1KnAY6PsItiI7gHN7hLivJvxaC-TfWf58DVf1EM27eU92XwFuA2Xz5kvce148aEZ44AFXGzJ9MWv6-pVgerUkL5EoMaJSVKtTHHYJyDCc9lzvhGNwK8CTUs8mEdDQDcs00cV0"
                    alt="Radar Scan"
                  />
                  <div className="radar-overlay"></div>
                  <div className="radar-info">
                    <div>
                      <p className="cell-id">CELL ID: #H-9942</p>
                      <p className="location">Dallas-Fort Worth Metroplex</p>
                    </div>
                    <Maximize2 size={18} className="fullscreen-icon" />
                  </div>
                </div>
              </div>

              <div className="data-breakdown">
                <div className="stat-card">
                  <p className="label">Max Hail Size</p>
                  <p className="value highlight">2.75"</p>
                </div>
                <div className="stat-card">
                  <p className="label">Impacted Parcels</p>
                  <p className="value">6,400</p>
                </div>
                <div className="stat-card accent-border">
                  <p className="label">Est. Opportunity</p>
                  <p className="value">$4.2M</p>
                </div>
              </div>
            </div>

            <div className="card-footer">
              <div className="freshness">
                <Clock size={14} />
                <span>Data fresh as of 2 mins ago</span>
              </div>
              <button className="export-btn">
                <Download size={16} />
                EXPORT LEAD BATCH
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Right Sidebar: Live Feed */}
      <aside className="live-feed">
        <div className="feed-header">
          <h3>Live Feed</h3>
          <div className="monitoring-status">
            <span className="pulse-dot"></span>
            <span>MONITORING</span>
          </div>
        </div>

        <div className="feed-items">
          <div className="feed-item selected">
            <div className="item-header">
              <div className="type">
                <CloudRain size={14} className="icon-critical" />
                <span>SEVERE HAIL</span>
              </div>
              <span className="timestamp">JUST NOW</span>
            </div>
            <p className="item-location">Dallas-Fort Worth, TX</p>
            <p className="item-details">2.75" max size detected. High structural damage probability.</p>
          </div>

          <div className="feed-item">
            <div className="item-header">
              <div className="type">
                <CloudRain size={14} className="icon-warning" />
                <span>MODERATE HAIL</span>
              </div>
              <span className="timestamp">-14m</span>
            </div>
            <p className="item-location">Norman, OK</p>
            <p className="item-details">1.50" observed. Moderate impact expected.</p>
          </div>

          <div className="feed-item">
            <div className="item-header">
              <div className="type">
                <Wind size={14} className="icon-info" />
                <span>HIGH WIND</span>
              </div>
              <span className="timestamp">-32m</span>
            </div>
            <p className="item-location">Tulsa, OK</p>
            <p className="item-details">65mph gusts recorded. Roof damage possible.</p>
          </div>
        </div>
      </aside>
    </div>
  );
}
