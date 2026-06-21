import "../../styles/panels.css";
import { LegendItem } from "../ui/LegendItem";

export function Legend() {
  return (
    <div>
      <LegendItem lineColor="#ff2d78" label="Muon μ⁺"         sub="Positive · pink track" />
      <LegendItem lineColor="#00e5ff" label="Muon μ⁻"         sub="Negative · cyan track" />
      <LegendItem dotColor="#ffd700"  label="Collision vertex" sub="Gold = Z boson event" />
      <LegendItem lineColor="#1e3a5f" label="CMS detector"     sub="Concentric barrel layers" />
    </div>
  );
}