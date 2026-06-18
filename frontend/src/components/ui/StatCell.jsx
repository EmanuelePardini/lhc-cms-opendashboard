import "../../styles/panels.css";

export function StatCell({ num, label, color }) {
  return (
    <div className="stat-cell">
      <div className="stat-cell__num" style={color ? { color } : undefined}>{num}</div>
      <div className="stat-cell__lbl">{label}</div>
    </div>
  );
}