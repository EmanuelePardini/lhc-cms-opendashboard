import "../../styles/panels.css";

export function InfoRow({ label, value, color }) {
  return (
    <div className="info-row">
      <span className="info-row__key">{label}</span>
      <span className="info-row__val" style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}