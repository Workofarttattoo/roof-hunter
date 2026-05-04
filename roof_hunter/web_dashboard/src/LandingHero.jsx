import { Sparkles, Satellite, HeartHandshake, Zap, ArrowRight, Radar } from 'lucide-react';

const HERO_IMG =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuCxwL1EBhF-Ui2WukWXQ_cIeQ0lmAL0XK0a-v7fJR0WAt8mZ2wZZEvMMvXvyavDYMvWkRsUIMx-GnDJpsxx44JvJF_mqJtKzt5qe7q1DnphRT1QgO24jB8Z--NP5U7CKbOdwAvRU9SXhA0D1FJfeZKZkFZD7oac1bxjACfPHmRtemmFFW2YNWpC589qRS2UZp6Cc7-yVZDWumvToDSY5qvOxbJ6yxtBy_ZYBfn7rXsarZesOGvB9t7eDaYnWWkf2VAf64c5Mjz90tqk';

export default function LandingHero({
  totalLeadsLabel,
  onBrowseLeads,
  onSignIn,
  onTalkToAgent,
}) {
  return (
    <section className="rh-pro-hero" aria-labelledby="landing-hero-title">
      <div className="rh-pro-hero-bg">
        <img src={HERO_IMG} alt="" className="rh-pro-hero-img" />
        <div className="rh-pro-hero-gradient" />
      </div>
      <div className="rh-pro-hero-grid">
        <div className="rh-pro-hero-main">
          <div className="rh-pro-eyebrow">
            <span className="rh-pro-dot" aria-hidden />
            <span>Live storm intel · NOAA / NWS aligned</span>
          </div>
          <h2 id="landing-hero-title" className="landing-hero-title rh-pro-display">
            Outpace the storm.
            <span className="rh-pro-accent"> Dominate the lead.</span>
          </h2>
          <p className="landing-hero-lead rh-pro-lead">
            Precision meteorological targeting for contractors who need hyper-local hail impact and vulnerable property
            signals — faster than scraping stale lists. Powered by <strong>Ridgeline</strong> forensic pipeline and this
            marketplace.
          </p>
          <ul className="landing-incentives" aria-label="Platform advantages">
            <li>
              <Satellite size={18} className="inc-ic" aria-hidden />
              <span>
                <strong>Freshest evidence we have</strong> — satellite-forward tiles and damage index for honest calls.
              </span>
            </li>
            <li>
              <Sparkles size={18} className="inc-ic" aria-hidden />
              <span>
                <strong>ZIP &amp; corridor priority</strong> — see today&apos;s SPC-fed hail map, then claim inventory.
              </span>
            </li>
            <li>
              <HeartHandshake size={18} className="inc-ic" aria-hidden />
              <span>
                <strong>Community-first talk tracks</strong> — education and verification before hard close.
              </span>
            </li>
          </ul>
          <div className="landing-cta-row">
            <button type="button" className="cta-btn-primary lg rh-pro-cta-solid" onClick={onBrowseLeads}>
              <Zap size={18} aria-hidden /> See storm-matched leads
            </button>
            <button type="button" className="cta-btn-secondary lg" onClick={onSignIn}>
              <Radar size={18} aria-hidden /> Sign in to unlock
            </button>
            <button type="button" className="cta-btn-ghost lg" onClick={onTalkToAgent}>
              Talk to voice agent <ArrowRight size={18} aria-hidden />
            </button>
          </div>
          {totalLeadsLabel != null && (
            <p className="landing-stat-hint muted small">
              <strong>{totalLeadsLabel}</strong> contacts in-network — API-linked when deployed.
            </p>
          )}
        </div>
        <aside className="rh-pro-intel" aria-label="System status">
          <div className="rh-pro-intel-deco" aria-hidden>
            <span className="material-symbols-outlined rh-pro-sat-icon">satellite_alt</span>
          </div>
          <h3 className="rh-pro-intel-title">System intel</h3>
          <dl className="rh-pro-intel-rows">
            <div className="rh-pro-intel-row">
              <dt>Data sources</dt>
              <dd>SPC · NWS · ingest DB</dd>
            </div>
            <div className="rh-pro-intel-row">
              <dt>Map refresh</dt>
              <dd>Today / yesterday + archive</dd>
            </div>
            <div className="rh-pro-intel-row">
              <dt>Engine</dt>
              <dd className="rh-pro-intel-highlight">Ridgeline</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
