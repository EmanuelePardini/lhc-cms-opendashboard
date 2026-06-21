import { useEffect, useRef } from "react";
import { initScene } from "../three/buildScene";

export function SceneCanvas({ event, animationRef }) {
  const canvasRef  = useRef(null);
  const cleanupRef = useRef(null);
  const internalAnimRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null; }

    requestAnimationFrame(() => {
      cleanupRef.current = initScene(canvas, event, internalAnimRef);
      // Dopo che initScene ha popolato internalAnimRef, copiamo i metodi nel ref esterno
      if (animationRef) {
        animationRef.current = internalAnimRef.current;
      }
    });

    return () => { if (cleanupRef.current) cleanupRef.current(); };
  }, [event]);

  return (
    <canvas
      ref={canvasRef}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", display: "block" }}
    />
  );
}