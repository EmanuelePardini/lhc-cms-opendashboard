import "../../styles/panels.css";
import { fmt } from "../../utils/physics";

export function EventSelector({ events, selected, loading, page, hasMore, zOnly, onSelect, onRefresh, onNext, onPrev, onToggleZOnly }) {
  return (
    <div style={{ width: 260 }}>
      <div className="events__filter-row">
        <span className="events__filter-label">Filter</span>
        <button
          className={`btn-toggle ${zOnly ? "btn-toggle--active" : ""}`}
          onClick={() => onToggleZOnly(!zOnly)}
        >
          Z Boson only
        </button>
        <button
          className="btn-toggle"
          onClick={() => onRefresh(page, zOnly)}
          disabled={loading}
          style={{ marginLeft: "auto" }}
        >
          ↻
        </button>
      </div>

      <div className="event-list">
        {events.map(ev => (
          <div
            key={ev.id}
            className={`event-item ${selected?.id === ev.id ? "event-item--selected" : ""}`}
            onClick={() => onSelect(ev)}
          >
            <div>
              <div className="event-item__id">#{ev.id}</div>
              <div className="event-item__run">Run {ev.run}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="event-item__mass">{fmt(ev.invariant_mass)} GeV</div>
              {ev.z_candidate === 1 && <div className="event-item__badge">Z</div>}
            </div>
          </div>
        ))}
        {events.length === 0 && !loading && (
          <div className="event-list__empty">No events found</div>
        )}
      </div>

      <div className="pagination">
        <button className="pagination__btn" onClick={onPrev} disabled={page === 0 || loading}>‹</button>
        <span className="pagination__label">{loading ? "…" : `Page ${page + 1}`}</span>
        <button className="pagination__btn" onClick={onNext} disabled={!hasMore || loading}>›</button>
      </div>
    </div>
  );
}