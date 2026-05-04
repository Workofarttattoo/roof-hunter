import { useState } from 'react';
import { Sparkles, ChevronUp } from 'lucide-react';

export default function SiteWideCtaBar({ onBrowseLeads, onSignIn, visible = true }) {
  const [open, setOpen] = useState(true);
  if (!visible) return null;
  return (
    <div className={`site-cta-bar glass ${open ? 'is-open' : 'is-collapsed'}`} role="region" aria-label="Call to action">
      {open ? (
        <div className="site-cta-inner">
          <div className="site-cta-copy">
            <strong>Don&apos;t miss another storm cycle.</strong>{' '}
            <span className="muted">
              Ridgeline-only leads, freshest roof intelligence, help homeowners first — grow with your community.
            </span>
          </div>
          <div className="site-cta-actions">
            <button type="button" className="cta-btn-primary sm" onClick={onBrowseLeads}>
              <Sparkles size={16} /> Grab leads now
            </button>
            <button type="button" className="cta-btn-ghost sm" onClick={onSignIn}>
              Sign in
            </button>
            <button type="button" className="site-cta-toggle" onClick={() => setOpen(false)} aria-expanded={open}>
              Hide <ChevronUp size={16} />
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="site-cta-peek" onClick={() => setOpen(true)} aria-expanded={open}>
          <Sparkles size={14} /> You&apos;re missing leads — show offer
        </button>
      )}
    </div>
  );
}
