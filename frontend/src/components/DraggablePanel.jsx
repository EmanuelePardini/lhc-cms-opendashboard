import { useState } from "react";
import { useDraggable } from "../hooks/useDraggable";
import "../styles/draggable.css";

export function DraggablePanel({ id, title, initialPos, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  const { ref, pos, isDragging, docks, onMouseDown } = useDraggable(id, initialPos);

  const dockClass = Object.entries(docks)
    .filter(([, v]) => v)
    .map(([k]) => `docked--${k}`)
    .join(" ");

  return (
    <div
      ref={ref}
      className={`draggable-panel ${isDragging ? "draggable-panel--dragging" : ""} ${dockClass}`}
      style={{ left: pos.x, top: pos.y }}
    >

      <div className="draggable-panel__header" onMouseDown={onMouseDown}>
        <span className="draggable-panel__title">{title}</span>
        <div className="panel__controls">
          <button
            className={`draggable-panel__toggle ${open ? "" : "draggable-panel__toggle--closed"}`}
            onClick={() => setOpen(v => !v)}
            title={open ? "Collapse" : "Expand"}
          >
            ‹
          </button>
        </div>
      </div>

      <div className={`draggable-panel__body ${open ? "" : "draggable-panel__body--hidden"}`}>
        {children}
      </div>
    </div>
  );
}