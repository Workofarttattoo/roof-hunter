import React from 'react';
import { Target, Zap, TrendingUp, Shield, BarChart3, Rocket, Download, PhoneCall } from 'lucide-react';

const CommandCenter = () => {
  return (
    <div className="command-center grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4">
      {/* PANEL 1 — STORM DECISION ENGINE */}
      <div className="glass-premium p-4 rounded-xl border border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="text-yellow-400" size={20} />
          <h3 className="font-bold text-lg">Storm Decision Engine</h3>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-400">Storm Alpha</span>
            <span className="text-green-400 font-bold">Active</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Confidence</span>
            <span className="font-mono">82%</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">ETA</span>
            <span className="font-mono">42 min</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Impact Zone</span>
            <span className="font-bold">Edmond North</span>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button className="flex-1 bg-blue-600 hover:bg-blue-700 text-xs py-2 rounded font-bold transition-colors">
            DEPLOY CREWS
          </button>
          <button className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-xs py-2 rounded font-bold transition-colors">
            PUSH TO CALL CENTER
          </button>
        </div>
      </div>

      {/* PANEL 2 — REVENUE PROJECTION */}
      <div className="glass-premium p-4 rounded-xl border border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="text-green-400" size={20} />
          <h3 className="font-bold text-lg">Revenue Projection</h3>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-400">Homes in Path</span>
            <span className="font-mono">312</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">High Value Targets</span>
            <span className="font-mono">94</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Close Rate</span>
            <span className="font-mono">18%</span>
          </div>
          <div className="mt-4 pt-2 border-t border-white/5">
            <div className="text-xs text-gray-400">Projected Revenue</div>
            <div className="text-2xl font-bold text-green-400">$128,000</div>
          </div>
        </div>
      </div>

      {/* PANEL 3 — TARGET LIST (CRITICAL) */}
      <div className="glass-premium p-4 rounded-xl border border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Target className="text-red-400" size={20} />
          <h3 className="font-bold text-lg">Top Targets</h3>
        </div>
        <div className="space-y-3">
          {[
            { id: 1, address: "123 Oak St", score: 0.91 },
            { id: 2, address: "456 Pine St", score: 0.87 },
            { id: 3, address: "789 Elm St", score: 0.84 },
          ].map((t) => (
            <div key={t.id} className="flex justify-between items-center bg-white/5 p-2 rounded">
              <span className="text-sm truncate mr-2">{t.address}</span>
              <span className="text-xs font-mono bg-red-500/20 text-red-400 px-2 py-0.5 rounded border border-red-500/30">
                {t.score.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex flex-col gap-2">
          <button className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 text-xs py-2 rounded transition-colors">
            <Download size={14} /> EXPORT CSV
          </button>
          <button className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-xs py-2 rounded font-bold transition-colors">
             <Rocket size={14} /> AUTO DEPLOY TARGETS
          </button>
        </div>
      </div>

      {/* PANEL 4 — TRUST / PROOF */}
      <div className="glass-premium p-4 rounded-xl border border-white/10">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="text-blue-400" size={20} />
          <h3 className="font-bold text-lg">System Performance</h3>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] text-gray-400 uppercase">Detection</div>
            <div className="text-xl font-bold">78%</div>
          </div>
          <div>
            <div className="text-[10px] text-gray-400 uppercase">Precision</div>
            <div className="text-xl font-bold">72%</div>
          </div>
          <div>
            <div className="text-[10px] text-gray-400 uppercase">Avg Lead Time</div>
            <div className="text-xl font-bold text-green-400">+21m</div>
          </div>
          <div>
            <div className="text-[10px] text-gray-400 uppercase">Dist Error</div>
            <div className="text-xl font-bold">11 km</div>
          </div>
        </div>
        <div className="mt-4 text-[10px] text-gray-500 italic">
          Last 30 days trailing performance
        </div>
      </div>
    </div>
  );
};

export default CommandCenter;
