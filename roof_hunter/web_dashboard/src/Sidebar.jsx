import { Radar, Rss, Crosshair, Building2, Archive, HelpCircle, Activity, DollarSign } from 'lucide-react';

const OPS_AVATAR =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuBVp0rk4ONxVxg53Rc1AdSpM8lNVb4tGpxqGI23Bdb98b4ta6RDSx7yZ2_tR01xmgM-LfpVuJdbvzHJnX0YSqxZW0RgVO2qhIgMW2ZBvYrq_PIW21zMxBq6xZqZLy1m5i7_Mg2Hr8iUDlWekRO-BPIZoWMpACpa48IrLDGU7MDJgx3z73nCSMO0qoSCvfxriyBdEDSQlD6Ru1ud7RxUpF-PxBaK7ZLAmDW_4S2woIMnToeHye1myTGOegAY6wKRfdB-cMD29syO5Ccu';

const NAV_ITEMS = [
  { id: 'storm_intel', label: 'Live Radar', Icon: Radar },
  { id: 'noaa_feeds', label: 'NOAA Feeds', Icon: Rss },
  { id: 'marketplace', label: 'Lead Manager', Icon: Crosshair },
  { id: 'property_intel', label: 'Property Intel', Icon: Building2 },
  { id: 'pricing', label: 'Pricing & ROI', Icon: DollarSign },
  { id: 'flyover', label: 'Archive', Icon: Archive },
];

export default function Sidebar({ activeTab, setActiveTab }) {
  return (
    <aside className="ops-sidebar" aria-label="Operations navigation">
      <div className="ops-sidebar-brand">
        <img src={OPS_AVATAR} alt="" className="ops-avatar" aria-hidden />
        <div>
          <h2 className="ops-brand-name">Ops Center</h2>
          <p className="ops-brand-sub">Severe Weather Tracking</p>
        </div>
      </div>

      <nav className="ops-nav">
        {NAV_ITEMS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            className={`ops-nav-item${activeTab === id ? ' active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={18} aria-hidden />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="ops-sidebar-cta">
        <button
          type="button"
          className="ops-generate-btn"
          onClick={() => setActiveTab('marketplace')}
        >
          Generate Lead Report
        </button>
      </div>

      <div className="ops-sidebar-util">
        <a href="#" className="ops-util-link">
          <HelpCircle size={15} aria-hidden /> Support
        </a>
        <a href="#" className="ops-util-link">
          <Activity size={15} aria-hidden /> System Status
        </a>
      </div>
    </aside>
  );
}
