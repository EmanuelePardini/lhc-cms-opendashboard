import "../../styles/panels.css";

export function SectionDivider({ label, color }) {
  return (
    <div className="section-divider">
      <span style={{ color }}>{label}</span>
      <div className="section-divider__line" />
    </div>
  );
}