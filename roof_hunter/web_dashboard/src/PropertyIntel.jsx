import { CheckCircle2, XCircle, ShieldCheck, Zap, Database, Crosshair } from 'lucide-react';

const CHECK = <CheckCircle2 size={20} className="pi-check" aria-label="Yes" />;
const CROSS = <XCircle size={20} className="pi-cross" aria-label="No" />;

const TABLE_ROWS = [
  {
    feature: 'Strike Zone Prediction',
    rh: (
      <>
        <strong>1-Year Lead Time</strong>
        <br />
        <span className="pi-sub">75% Accuracy</span>
      </>
    ),
    hailtrace: 'Hours Behind',
    nearmap: 'Historical Only',
  },
  {
    feature: 'Predictive Outreach',
    rh: (
      <>
        <span className="pi-star">✦</span>
        <br />
        <strong>Predict &amp; Prevent</strong>
      </>
    ),
    hailtrace: 'Reactive Only',
    nearmap: CROSS,
  },
  {
    feature: 'Street-Level Property Intel',
    rh: CHECK,
    hailtrace: 'Limited',
    nearmap: CHECK,
  },
  {
    feature: 'Automated Lead Scoring',
    rh: CHECK,
    hailtrace: 'Manual Export',
    nearmap: CROSS,
  },
  {
    feature: 'Post-Storm Aerial Refresh',
    rh: (
      <>
        <strong>5-Day Sat</strong>
        <br />
        <span className="pi-sub">48h UAV/Drone (OK Zones)</span>
      </>
    ),
    hailtrace: 'N/A',
    nearmap: 'Varies (Weeks)',
  },
  {
    feature: 'API Integration',
    rh: CHECK,
    hailtrace: 'Add-on Cost',
    nearmap: CHECK,
  },
];

const METRICS = [
  {
    Icon: Zap,
    title: 'Prediction Engine',
    big: '1-Year Strike Zone',
    body: "Wizard-like predictive capabilities with 75% accuracy. Prepare outreach weeks in advance and 'Predict & Prevent' damages before they occur.",
  },
  {
    Icon: Crosshair,
    title: 'Precision Accuracy',
    big: '100%',
    body: 'Zero-margin error in mapping. 100% of our generated predictions are verified correct over 90-day field testing.',
  },
  {
    Icon: Database,
    title: 'Data Depth',
    big: '15yr',
    body: 'Historical archive access, allowing comprehensive property damage analysis.',
  },
];

export default function PropertyIntel() {
  return (
    <div className="pi-page fade-in">
      {/* Hero */}
      <section className="pi-hero">
        <h1 className="pi-display">Unmatched Property Intelligence</h1>
        <p className="pi-hero-lead muted">
          See how Roof Hunter Pro delivers superior data depth, faster updates, and actionable lead generation
          compared to legacy systems.
        </p>
      </section>

      {/* Mobilize callout */}
      <section className="pi-mobilize glass">
        <h2 className="pi-mobilize-title">Mobilize in Unsaturated Markets</h2>
        <p className="pi-mobilize-body">
          Be a Community Hero: Mobilize your sales team in unsaturated markets before they even know a storm is
          coming. Predict, prevent, and protect.
        </p>
      </section>

      {/* Comparison table */}
      <section className="pi-table-section glass">
        <h2 className="pi-section-title">Roof Hunter Pro vs. The Competition</h2>
        <div className="pi-table-scroll">
          <table className="pi-table">
            <thead>
              <tr>
                <th className="pi-th-feature">Feature</th>
                <th className="pi-th-rh">Roof Hunter Pro</th>
                <th>HailTrace</th>
                <th>Nearmap</th>
              </tr>
            </thead>
            <tbody>
              {TABLE_ROWS.map(({ feature, rh, hailtrace, nearmap }) => (
                <tr key={feature}>
                  <td className="pi-td-feature">{feature}</td>
                  <td className="pi-td-rh">{rh}</td>
                  <td className="pi-td-comp">{hailtrace}</td>
                  <td className="pi-td-comp">{nearmap}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Key metrics grid */}
      <section className="pi-metrics">
        {METRICS.map(({ Icon, title, big, body }) => (
          <div key={title} className="pi-metric-card glass">
            <div className="pi-metric-deco" aria-hidden>
              <Icon size={72} />
            </div>
            <h3 className="pi-metric-title">{title}</h3>
            <p className="pi-metric-big">{big}</p>
            <p className="pi-metric-body muted">{body}</p>
          </div>
        ))}
      </section>

      {/* Verified field testing */}
      <section className="pi-verified glass">
        <div className="pi-verified-deco" aria-hidden>✓</div>
        <div className="pi-verified-inner">
          <h2 className="pi-verified-title">
            <ShieldCheck size={22} aria-hidden /> Verified Field Testing
          </h2>
          <div className="pi-verified-grid">
            <div className="pi-verified-stat">
              <p className="pi-metric-big">75%</p>
              <h3>Strike Recall</h3>
              <p className="muted">
                Predicting 75% of severe weather events a full year in advance, allowing for unparalleled market
                positioning.
              </p>
            </div>
            <div className="pi-verified-stat">
              <p className="pi-metric-big">100%</p>
              <h3>Precision Accuracy</h3>
              <p className="muted">
                100% of our predictions are verified correct. We prioritize absolute accuracy to ensure your team
                never chases a false lead.
              </p>
            </div>
          </div>
          <p className="pi-footnote muted">
            *Comparative study based on 90-day concurrent field testing against HailTrace property datasets.
          </p>
        </div>
      </section>
    </div>
  );
}
