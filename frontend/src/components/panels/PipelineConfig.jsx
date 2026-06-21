import "../../styles/panels.css";
import { InfoRow }        from "../ui/InfoRow";
import { SectionDivider } from "../ui/SectionDivider";

export function PipelineConfig({ config, loading }) {
  // 1. Loading state aligned with dashboard style
  if (loading) {
    return (
      <div style={{ width: 260 }}>
        <p className="explain-text explain-text--muted">
          Loading active filters...
        </p>
      </div>
    );
  }

  // 2. Error state 
  if (!config || !config.cuts) {
    return (
      <div style={{ width: 260 }}>
        <p className="explain-text explain-text--muted">
          No active configuration detected from backend.
        </p>
      </div>
    );
  }

  // 3. Actual data rendering
  return (
    <div style={{ width: 260 }}>
      <p className="explain-text" style={{ marginBottom: 12 }}>
        Current <b style={{ color: "#0033a0" }}>Analysis Engine</b> parameters 
        applied to the dataset to filter collision events.
      </p>

      <SectionDivider label="Kinematic Cuts" color="#c0392b" />

      {Object.entries(config.cuts).map(([key, value]) => (
        <InfoRow 
          key={key} 
          label={key} 
          value={value !== null ? String(value) : "null"} 
        />
      ))}
    </div>
  );
}