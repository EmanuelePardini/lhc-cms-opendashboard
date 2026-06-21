import { useState, useRef, useCallback, useEffect } from "react";

const DOCK_THRESHOLD = 60;
const PANEL_GAP      = 16;
const HEADER_HEIGHT  = 62;

function snapToDock(x, y, w, h, vw, vh) {
  const docks = {
    left:   x < DOCK_THRESHOLD,
    right:  x + w > vw - DOCK_THRESHOLD,
    top:    y < DOCK_THRESHOLD + HEADER_HEIGHT,
    bottom: y + h > vh - DOCK_THRESHOLD,
  };

  let snappedX = x;
  let snappedY = y;

  if (docks.left)   snappedX = PANEL_GAP;
  if (docks.right)  snappedX = vw - w - PANEL_GAP;
  if (docks.top)    snappedY = HEADER_HEIGHT + PANEL_GAP;
  if (docks.bottom) snappedY = vh - h - PANEL_GAP;

  return { x: snappedX, y: snappedY, docks };
}

export function useDraggable(id, initialPos) {
  const [pos,       setPos]       = useState(initialPos);
  const [isDragging, setIsDragging] = useState(false);
  const [docks,     setDocks]     = useState({});
  const ref        = useRef(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  // Persist position
  useEffect(() => {
    const saved = localStorage.getItem(`panel-pos-${id}`);
    if (saved) {
      try { setPos(JSON.parse(saved)); } catch {}
    }
  }, [id]);

  const onMouseDown = useCallback(e => {
    if (e.target.closest(".panel__controls")) return;
    e.preventDefault();
    const rect = ref.current.getBoundingClientRect();
    dragOffset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const onMouseMove = e => {
      const el = ref.current;
      if (!el) return;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const w  = el.offsetWidth;
      const h  = el.offsetHeight;

      const rawX = e.clientX - dragOffset.current.x;
      const rawY = e.clientY - dragOffset.current.y;

      const clamped = {
        x: Math.max(0, Math.min(rawX, vw - w)),
        y: Math.max(HEADER_HEIGHT, Math.min(rawY, vh - h)),
      };

      const { x, y, docks: d } = snapToDock(clamped.x, clamped.y, w, h, vw, vh);
      setPos({ x, y });
      setDocks(d);
    };

    const onMouseUp = () => {
      setIsDragging(false);
      localStorage.setItem(`panel-pos-${id}`, JSON.stringify(pos));
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup",   onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup",   onMouseUp);
    };
  }, [isDragging, id, pos]);

  return { ref, pos, isDragging, docks, onMouseDown };
}