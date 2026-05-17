import { useState } from 'react';
import { CheckCircle2, Calculator, Zap } from 'lucide-react';

const TIERS = [
  {
    name: 'Tactical',
    price: '$499',
    period: '/mo',
    desc: 'Essential radar telemetry for independent operators.',
    featured: false,
    cta: 'Deploy Tactical',
    features: [
      'Live Radar Access (Regional)',
      'Standard NOAA Feed',
      'Up to 500 Property Lookups',
    ],
  },
  {
    name: 'Strategic Ops',
    price: '$1,299',
    period: '/mo',
    desc: 'Advanced intelligence for multi-crew scaling.',
    featured: true,
    cta: 'Initialize Strategic',
    features: [
      'National Live Radar & Archive',
      'Sub-2s Data Latency',
      'Unlimited Property Lookups',
      'Lead Manager Integration',
    ],
  },
  {
    name: 'Enterprise Command',
    price: 'Custom Spec',
    period: '',
    desc: 'Unrestricted access and API integrations for national carriers.',
    featured: false,
    cta: 'Request Protocols',
    features: [
      'Full API Access',
      'Custom White-labeling',
      'Dedicated Account Engineer',
    ],
  },
];

const fmt = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);

function calcROI(jobSize, volume, closeRate) {
  const monthlyJobs = volume * (closeRate / 100);
  const gross = monthlyJobs * jobSize * 12;
  const cost = 18000;
  return { gross, cost, profit: gross - cost };
}

export default function PricingROI() {
  const [jobSize, setJobSize] = useState(18500);
  const [volume, setVolume] = useState(150);
  const [closeRate, setCloseRate] = useState(12);
  const roi = calcROI(jobSize, volume, closeRate);

  return (
    <div className="pricing-page fade-in">
      {/* ROI Calculator Hero */}
      <section className="pricing-hero glass">
        <div className="pricing-hero-left">
          <div className="pricing-badge">
            <Calculator size={13} aria-hidden /> ROI Engine
          </div>

          <div className="pricing-accuracy-bar glass-inset">
            <CheckCircle2 size={15} className="pi-check" aria-hidden />
            <strong>100% Accurate Lead Verification</strong>
            <p className="muted">
              Our precision engine identifies verified damage targets with absolute certainty,{' '}
              <strong>eliminating wasted spend on false positives</strong> and ensuring your team only deploys where
              the strike occurred.
            </p>
          </div>

          <h1 className="pricing-display">
            The Math of<br />Dominance.
          </h1>
          <p className="pricing-lead muted">
            Dial in your operational metrics to forecast the exponential revenue growth unlocked by precision storm
            data.
          </p>

          <div className="pricing-sliders">
            <label className="pricing-slider-label">
              <div className="pricing-slider-row">
                <span>Average Job Size</span>
                <strong className="pricing-slider-val">{fmt(jobSize)}</strong>
              </div>
              <input
                type="range" min={5000} max={50000} step={500} value={jobSize}
                onChange={(e) => setJobSize(Number(e.target.value))}
                className="pricing-range"
              />
            </label>
            <label className="pricing-slider-label">
              <div className="pricing-slider-row">
                <span>Target Lead Volume (Monthly)</span>
                <strong className="pricing-slider-val">{volume}</strong>
              </div>
              <input
                type="range" min={10} max={500} step={5} value={volume}
                onChange={(e) => setVolume(Number(e.target.value))}
                className="pricing-range"
              />
            </label>
            <label className="pricing-slider-label">
              <div className="pricing-slider-row">
                <span>Historical Close Rate</span>
                <strong className="pricing-slider-val">{closeRate}%</strong>
              </div>
              <input
                type="range" min={1} max={50} step={1} value={closeRate}
                onChange={(e) => setCloseRate(Number(e.target.value))}
                className="pricing-range"
              />
            </label>
          </div>
        </div>

        <div className="pricing-result glass-premium">
          <div className="pricing-result-pulse" aria-hidden>
            <span className="pulse" />
          </div>
          <h3 className="pricing-result-label">Calculated Annual Profit</h3>
          <div className="pricing-result-number">{fmt(roi.profit)}</div>
          <div className="pricing-result-divider" />
          <div className="pricing-result-breakdown">
            <div>
              <div className="pricing-result-sub-label">Gross Revenue</div>
              <div className="pricing-result-sub-val">{fmt(roi.gross)}</div>
            </div>
            <div>
              <div className="pricing-result-sub-label">Cost of Data</div>
              <div className="pricing-result-sub-val">-{fmt(roi.cost)}</div>
            </div>
          </div>
          <button type="button" className="cta-btn-primary pricing-deploy-btn">
            <Zap size={16} aria-hidden /> Initialize Deployment
          </button>
        </div>
      </section>

      {/* Pricing tiers */}
      <section className="pricing-tiers-section">
        <div className="pricing-tiers-header">
          <h2 className="pricing-tiers-title">Technical Specifications</h2>
          <p className="muted">Select the operational capacity required for your command center.</p>
        </div>
        <div className="pricing-tiers">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`pricing-tier glass${tier.featured ? ' pricing-tier--featured' : ''}`}
            >
              {tier.featured && <div className="pricing-tier-badge">Recommended Spec</div>}
              <h3 className={`pricing-tier-name${tier.featured ? ' pricing-tier-name--cyan' : ''}`}>
                {tier.name}
              </h3>
              <div className="pricing-tier-price">
                <span className="pricing-tier-amount">{tier.price}</span>
                {tier.period && <span className="pricing-tier-period">{tier.period}</span>}
              </div>
              <p className="pricing-tier-desc muted">{tier.desc}</p>
              <div className="pricing-tier-divider" />
              <ul className="pricing-tier-features">
                {tier.features.map((f) => (
                  <li key={f}>
                    <CheckCircle2 size={15} className="pi-check" aria-hidden /> {f}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className={`pricing-tier-cta ${tier.featured ? 'cta-btn-primary' : 'cta-btn-secondary'}`}
              >
                {tier.cta}
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
