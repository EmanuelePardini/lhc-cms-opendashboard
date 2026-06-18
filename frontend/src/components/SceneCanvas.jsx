import { useScene } from "../hooks/useScene";

export function SceneCanvas({ event }) {
  const canvasRef = useScene(event);
  return (
    <canvas
      ref={canvasRef}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", display: "block" }}
    />
  );
}