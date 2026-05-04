import { BarChart3, AlertTriangle, ArrowRight } from 'lucide-react';

/**
 * Feature grid aligned with Stitch landing_page_v3 “Engineered for Dominance” bento.
 */
export default function BentoFeatures({ onBrowseLeads }) {
  return (
    <section className="bento-features" aria-labelledby="bento-features-title">
      <div className="bento-features-inner">
        <div className="bento-intro">
          <h2 id="bento-features-title" className="bento-title">
            Engineered for dominance
          </h2>
          <p className="bento-sub">
            Stop relying on outdated, generic data. Roof Hunter Pro delivers granular, property-specific signals — NOAA /
            NWS storm context, MRMS-capable pipeline, and forensic scoring in one command surface (Ridgeline).
          </p>
        </div>
        <div className="bento-grid">
          <article className="bento-card bento-card--wide bento-card--media">
            <div className="bento-media bento-media--aerial" aria-hidden />
            <div className="bento-media-fade" />
            <div className="bento-card-copy">
              <h3>Ultra-res property context</h3>
              <p>
                Pinpoint damage narratives with satellite-forward evidence and storm correlation — not generic maps.
              </p>
            </div>
          </article>
          <article className="bento-card">
            <BarChart3 className="bento-icon" size={36} strokeWidth={1.5} aria-hidden />
            <h3>Predictive scoring</h3>
            <p>Rank corridors and contacts by hail severity, damage index, and freshness — before the competition.</p>
            <p className="bento-foot">
              <span className="bento-check">Live SPC + ingest pipeline</span>
            </p>
          </article>
          <article className="bento-card">
            <AlertTriangle className="bento-icon bento-icon--warn" size={36} strokeWidth={1.5} aria-hidden />
            <h3>Severe alerts</h3>
            <p>NWS-aware hail messaging layered with your marketplace — same app, same night.</p>
          </article>
          <article className="bento-card bento-card--wide bento-card--split">
            <div>
              <h3>Seamless CRM handoff</h3>
              <p className="bento-split-p">
                Push identified properties into your crew workflow; Square unlocks and API hooks where you deploy
                Ridgeline.
              </p>
            </div>
            <button type="button" className="bento-inline-cta" onClick={onBrowseLeads}>
              Open lead inventory <ArrowRight size={16} aria-hidden />
            </button>
          </article>
        </div>
      </div>
    </section>
  );
}
