import "../../styles/panels.css";
import { StatCell } from "../ui/StatCell";
import { fmt }      from "../../utils/physics";

export function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="panel panel--stats">
      <StatCell num={stats.total_events?.toLocaleString()} label="Total events" />
      <StatCell num={stats.z_candidates?.toLocaleString()} label="Z candidates"  color="#ffd700" />
      <StatCell num={`${fmt(stats.z_mass_mean_gev)} GeV`}  label="Z peak mass"   color="#ff2d78" />
      <StatCell num={`${fmt(stats.pt1_mean_gev)} GeV/c`}   label="Avg muon pT" />
    </div>
  );
}