import "../../styles/panels.css";

export function LegendItem({ lineColor, dotColor, label, sub }) {
  return (
    <div className="legend-item">
      {lineColor && <div className="legend-item__line" style={{ background: lineColor }} />}
      {dotColor  && <div className="legend-item__dot"  style={{ background: dotColor  }} />}
      <div>
        <div className="legend-item__label">{label}</div>
        <div className="legend-item__sub">{sub}</div>
      </div>
    </div>
  );
}