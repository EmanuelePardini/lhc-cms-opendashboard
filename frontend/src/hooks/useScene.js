import { useEffect, useRef } from "react";
import { initScene } from "../three/buildScene";

export function useScene(eventData) {
  const canvasRef  = useRef(null);
  const cleanupRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null; }
    requestAnimationFrame(() => {
      cleanupRef.current = initScene(canvas, eventData);
    });
    return () => { if (cleanupRef.current) cleanupRef.current(); };
  }, [eventData]);

  return canvasRef;
}