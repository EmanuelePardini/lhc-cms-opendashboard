import "../../styles/panels.css";
import { InfoRow }        from "../ui/InfoRow";
import { SectionDivider } from "../ui/SectionDivider";
import { fmt, describeEvent, recoTypeLabel } from "../../utils/physics";

export function EventInfo({ event }) {
  const info = describeEvent(event);

  if (!event) return (
    <div className="panel panel--info">
      <div className="panel-label">What am I looking at?</div>
      <p className="explain-text">
        Inside the <b style={{ color: "#ccd9f0" }}>Large Hadron Collider</b> at CERN, proton beams
        travelling near the speed of light collide billions of times per second.
      </p>
      <p className="explain-text">
        Each collision creates a burst of particles. This viewer shows real data from the{" "}
        <b style={{ color: "#ccd9f0" }}>CMS detector</b> — events where two{" "}
        <b style={{ color: "#ff2d78" }}>muons</b> (heavy cousins of the electron) were produced.
      </p>
      <p className="explain-text">
        By measuring their trajectories and energies, scientists can reconstruct the invisible
        parent particle — sometimes a <b style={{ color: "#ffd700" }}>Z boson</b>, sometimes
        something rarer.
      </p>
      <p className="explain-text explain-text--muted" style={{ marginTop: 14 }}>
        ← Select an event to begin.
      </p>
    </div>
  );

  return (
    <div className="panel panel--info">
      <div className="panel-label">Event details</div>

      {info && (
        <div className="info__card" style={{ borderLeftColor: info.color }}>
          <div className="info__card-tag" style={{ color: info.color }}>{info.tag}</div>
          <div className="info__card-desc">{info.desc}</div>
        </div>
      )}

      <InfoRow label="Combined mass"    value={`${fmt(event.invariant_mass)} GeV`} color="#ffd700" />
      <InfoRow label="Event ID"         value={`#${event.event}`}                  color="#00c8ff" />
      <InfoRow label="Run number"       value={event.run} />
      <InfoRow label="Angular sep. ΔR"  value={fmt(event.delta_r, 3)} />
      <InfoRow label="Opposite charges" value={event.opp_sign ? "Yes ✓" : "No ✗"} color={event.opp_sign ? "#4ade80" : "#f87171"} />

      <SectionDivider label="Muon 1" color="#ff2d78" />
      <InfoRow label="Momentum pT"  value={`${fmt(event.pt1)} GeV/c`} color="#ff2d78" />
      <InfoRow label="Direction η"  value={fmt(event.eta1, 3)} />
      <InfoRow label="Charge"       value={event.q1 > 0 ? "+1" : "−1"} />
      <InfoRow label="Reco type"    value={recoTypeLabel(event.type1)} />

      <SectionDivider label="Muon 2" color="#00e5ff" />
      <InfoRow label="Momentum pT"  value={`${fmt(event.pt2)} GeV/c`} color="#00e5ff" />
      <InfoRow label="Direction η"  value={fmt(event.eta2, 3)} />
      <InfoRow label="Charge"       value={event.q2 > 0 ? "+1" : "−1"} />
      <InfoRow label="Reco type"    value={recoTypeLabel(event.type2)} />
    </div>
  );
}