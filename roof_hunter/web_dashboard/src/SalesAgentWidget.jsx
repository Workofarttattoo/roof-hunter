import { createElement, useEffect, useState } from 'react';

/** Dashboard: “roof hunter sales agent” — override in web_dashboard/.env.local */
const PROD_SALES_AGENT_ID = 'agent_9601kq1b8dxkeh6snk5cjf4wb70h';
const WIDGET_MODULE = 'https://elevenlabs.io/convai-widget/index.js';

export default function SalesAgentWidget() {
  const agentId = import.meta.env.VITE_ELEVENLABS_SALES_AGENT_ID || PROD_SALES_AGENT_ID;
  const [ready, setReady] = useState(
    () => typeof customElements !== 'undefined' && !!customElements.get('elevenlabs-convai'),
  );
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (ready) return undefined;
    if (typeof customElements !== 'undefined' && customElements.get('elevenlabs-convai')) {
      setReady(true);
      return undefined;
    }
    const existing = document.querySelector('script[data-ridgeline-convai="1"]');
    if (existing) {
      const onLoad = () => setReady(true);
      const onErr = () => setFailed(true);
      existing.addEventListener('load', onLoad);
      existing.addEventListener('error', onErr);
      return () => {
        existing.removeEventListener('load', onLoad);
        existing.removeEventListener('error', onErr);
      };
    }
    const s = document.createElement('script');
    s.type = 'module';
    s.async = true;
    s.src = WIDGET_MODULE;
    s.dataset.ridgelineConvai = '1';
    s.onload = () => setReady(true);
    s.onerror = () => setFailed(true);
    document.head.appendChild(s);
    return undefined;
  }, [ready]);

  if (failed) {
    return (
      <p className="muted small sales-agent-widget-loading">
        Voice widget could not load (network, CSP, or blocker). Open the ElevenLabs dashboard to test the agent
        directly.
      </p>
    );
  }

  if (!ready) {
    return <p className="muted small sales-agent-widget-loading">Loading voice widget…</p>;
  }

  return createElement(
    'div',
    { className: 'sales-agent-widget-inner' },
    createElement('elevenlabs-convai', { 'agent-id': agentId }),
  );
}
