import { StatCell } from "../ui/StatCell";
import { HistogramItem } from "../ui/HistogramItem";
import { fmt } from "../../utils/physics";

export function StatsBar({ stats, histogram }) {
  if (!stats) return null;

  const data = (histogram?.bin_centers || []).map((c, i) => ({ 
    massBinCenter: c, 
    count: histogram.counts?.[i] || 0 
  }));
  const max = Math.max(...data.map(d => d.count), 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: "24px", padding: "6px 12px" }}>
      <StatCell num={stats.total_events?.toLocaleString()} label="Total events" />
      <StatCell num={stats.z_candidates?.toLocaleString()} label="Z candidates" color="#8a6500" />
      <StatCell num={`${fmt(stats.z_mass_mean_gev)} GeV`} label="Z peak" color="#c0392b" />
      <StatCell num={`${fmt(stats.pt1_mean_gev)} GeV/c`} label="Avg pT" />
      
      <StatCell 
        label="Mass Spectrum"
        num={
          <div style={{ display: "flex", alignItems: "flex-end", height: "20px", width: "120px", gap: "1px" }}>
            {data.map((bin, i) => (
              <HistogramItem key={i} bin={bin} maxCount={max} index={i} />
            ))}
          </div>
        }
      />
    </div>
  );
}