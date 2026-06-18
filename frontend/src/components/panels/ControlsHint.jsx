import "../../styles/panels.css";

export function ControlsHint() {
  return (
    <div className="panel panel--controls">
      <div>🖱  Drag to rotate</div>
      <div>⚲  Scroll to zoom</div>
      <div>↺  Auto-rotates when idle</div>
    </div>
  );
}