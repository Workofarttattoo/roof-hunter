import { ExternalLink, Cloud, BookOpen, Radio, LifeBuoy } from 'lucide-react';

const link = (href, label) => (
  <a href={href} target="_blank" rel="noopener noreferrer" className="noaa-spc-link">
    {label}
    <ExternalLink size={12} aria-hidden className="noaa-spc-ext" />
  </a>
);

/**
 * Curated official NOAA / NWS / SPC entry points — not a copy of government HTML.
 * Storm report tables change daily; ingest via CSV URLs in pipeline code instead.
 */
export default function NoaaSpcResources() {
  return (
    <details className="noaa-spc-resources glass-inset">
      <summary className="noaa-spc-summary">
        <Cloud size={18} className="noaa-spc-summary-icon" aria-hidden />
        <span>
          <strong>NOAA · NWS · Storm Prediction Center</strong>
          <span className="muted small noaa-spc-summary-sub">Official sources &amp; field reference (opens in new tab)</span>
        </span>
      </summary>

      <div className="noaa-spc-body">
        <p className="muted small noaa-spc-disclaimer">
          Local storm reports are <strong>preliminary</strong>. SPC &quot;day&quot; runs <strong>1200 UTC–1159 UTC</strong> the next
          calendar day. Hail <strong>Size</strong> in CSV is often hundredths of an inch (e.g. 175 → 1.75&quot;). Times are{' '}
          <strong>UTC</strong>. <strong>UNK</strong> means unknown. The site map merges SPC <strong>filtered hail CSVs</strong> for
          roughly the <strong>last 365 days</strong> (archive) plus <strong>today &amp; yesterday</strong> on a timer — same federal
          sources, US-wide, not state-scoped.
        </p>

        <div className="noaa-spc-columns">
          <div className="noaa-spc-col">
            <h4 className="noaa-spc-heading">Portals</h4>
            <ul className="noaa-spc-list">
              <li>{link('https://www.weather.gov/', 'Weather.gov (NWS)')}</li>
              <li>{link('https://www.noaa.gov/', 'NOAA')}</li>
              <li>{link('https://www.spc.noaa.gov/', 'Storm Prediction Center')}</li>
              <li>{link('https://www.facebook.com/NWSSPC', 'SPC on Facebook (@NWSSPC)')}</li>
              <li>{link('https://www.usa.gov/', 'USA.gov')}</li>
            </ul>
          </div>

          <div className="noaa-spc-col">
            <h4 className="noaa-spc-heading">SPC products</h4>
            <ul className="noaa-spc-list">
              <li>{link('https://www.spc.noaa.gov/products/', 'All SPC forecasts')}</li>
              <li>{link('https://www.spc.noaa.gov/products/watch/', 'Current watches')}</li>
              <li>{link('https://www.spc.noaa.gov/products/mcd/', 'Mesoscale discussions')}</li>
              <li>{link('https://www.spc.noaa.gov/products/outlook/', 'Convective outlooks')}</li>
              <li>{link('https://www.spc.noaa.gov/products/expert/', 'Thunderstorm outlooks')}</li>
              <li>{link('https://www.spc.noaa.gov/products/fire_wx/', 'Fire weather outlooks')}</li>
              <li>{link('https://www.spc.noaa.gov/rss/', 'RSS feeds')}</li>
            </ul>
          </div>

          <div className="noaa-spc-col">
            <h4 className="noaa-spc-heading">
              <BookOpen size={14} aria-hidden /> Weather information
            </h4>
            <ul className="noaa-spc-list">
              <li>{link('https://www.spc.noaa.gov/climo/reports/today.html', "Today's storm reports")}</li>
              <li>{link('https://www.spc.noaa.gov/climo/reports/today_filtered_hail.csv', 'Filtered hail (CSV, today)')}</li>
              <li>{link('https://www.spc.noaa.gov/climo/reports/yesterday_filtered_hail.csv', 'Filtered hail (CSV, yesterday)')}</li>
              <li>{link('https://www.spc.noaa.gov/climo/reports/', 'Storm reports directory (all dates / formats)')}</li>
              <li>{link('https://www.weather.gov/gis/hazmap', 'NWS hazards map')}</li>
              <li>{link('https://radar.weather.gov/', 'National radar')}</li>
              <li>{link('https://www.spc.noaa.gov/sfcfcst/', 'Product archive (SFC Fcst table)')}</li>
              <li>
                {link('https://www.weather.gov/nwr/', 'NOAA Weather Radio')}
              </li>
            </ul>
          </div>

          <div className="noaa-spc-col">
            <h4 className="noaa-spc-heading">Research &amp; education</h4>
            <ul className="noaa-spc-list">
              <li>{link('https://www.spc.noaa.gov/misc/spcfaq.html', 'SPC FAQ (lat/lon, units)')}</li>
              <li>{link('https://www.spc.noaa.gov/misc/AbtDerechos/derechofacts.htm', 'About derechos')}</li>
              <li>{link('https://www.spc.noaa.gov/misc/about.html', 'About the SPC')}</li>
              <li>{link('https://www.spc.noaa.gov/misc/spchistry.html', 'SPC history')}</li>
            </ul>
            <h4 className="noaa-spc-heading">
              <LifeBuoy size={14} aria-hidden /> Contact
            </h4>
            <ul className="noaa-spc-list">
              <li>{link('https://www.spc.noaa.gov/misc/spccontact.html', 'SPC contact &amp; feedback')}</li>
              <li>
                <span className="muted small">SPC: 120 David L. Boren Blvd., Norman, OK 73072 · </span>
                {link('mailto:spc.feedback@noaa.gov', 'spc.feedback@noaa.gov')}
              </li>
            </ul>
          </div>
        </div>

        <p className="muted small noaa-spc-foot">
          <Radio size={12} aria-hidden /> Static map graphic pattern documented by SPC:{' '}
          <code className="noaa-spc-code">https://www.spc.noaa.gov/climo/reports/YYMMDD_rpts.gif</code> · Printer-friendly HTML:{' '}
          <code className="noaa-spc-code">YYMMDD_prt_rpts.html</code> under the same path. Roof Hunter ingests filtered CSVs in{' '}
          <code className="noaa-spc-code">live_hail_ingest.py</code> — do not scrape this page for tables.
        </p>
      </div>
    </details>
  );
}
