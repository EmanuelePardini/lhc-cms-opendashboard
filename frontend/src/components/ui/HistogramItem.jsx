import { useState } from "react";

/**
 * * @param {Object} props
 * @param {Object} props.bin - The histogram bin object containing mass data and event count.
 * @param {number} props.bin.massBinCenter - The calculated center point value of the mass bin in GeV.
 * @param {number} props.bin.count - Total number of experimental events falling inside this bin.
 * @param {number} props.maxCount - The peak count value across all bins, used to scale the relative height.
 * @param {number} props.index - Array index position within the histogram dataset.
 */
export function HistogramItem({ bin, maxCount, index }) {
  // Local state to track mouse pointer proximity for dynamic highlight effects
  const [isHovered, setIsHovered] = useState(false);

  // Normalize the bin event count into a relative percentage for visual rendering
  const heightPercent = (bin.count / maxCount) * 100;

  // Define the Z0 electroweak neutral gauge boson invariant mass signal region window (86-96 GeV).
  // This allows the UI to visually distinguish the resonant peak from the continuum background.
  const isPeakRegion = bin.massBinCenter >= 86 && bin.massBinCenter <= 96;

  const barColor = isPeakRegion ? "rgba(192, 57, 43, 0.85)" : "rgba(56, 189, 248, 0.4)"; // Deep red for signal peak vs muted blue
  const hoverColor = isPeakRegion ? "#e74c3c" : "#38bdf8";  

  return (
    <div
      title={`Mass: ${bin.massBinCenter} GeV\nEvents: ${bin.count}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        flex: 1,
        height: bin.count > 0 ? `${Math.max(heightPercent, 3)}%` : "0%",
        background: isHovered ? hoverColor : barColor,
        transition: "height 0.3s ease, background-color 0.15s ease",
        cursor: "pointer",
        borderRadius: "1px 1px 0 0",
        position: "relative"
      }}
    />
  );
}