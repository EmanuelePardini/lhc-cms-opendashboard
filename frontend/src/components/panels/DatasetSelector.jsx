import "../../styles/panels.css";

export function DatasetSelector({ datasets, activeId, loading, error, query, onQueryChange, onSelect }) {
  if (loading) return <div className="datasets__loading">Loading…</div>;
  if (error)   return <div className="datasets__error">{error}</div>;

  return (
    <div style={{ width: 260 }}>
      <input
        className="datasets__search"
        type="text"
        placeholder="Search by name, year, energy…"
        value={query}
        onChange={e => onQueryChange(e.target.value)}
      />
      {datasets.length === 0 && (
        <div className="datasets__empty">No datasets match "{query}"</div>
      )}
      {datasets.map(ds => (
        <div
          key={ds.id}
          className={`dataset-item ${ds.id === activeId ? "dataset-item--active" : ""}`}
          onClick={() => onSelect(ds.id)}
        >
          <div className="dataset-item__header">
            <span className="dataset-item__label">{ds.label}</span>
            <span className="dataset-item__energy">{ds.energy}</span>
          </div>
          <div className="dataset-item__stats">
            <span>{ds.n_events?.toLocaleString()} events</span>
            <span className="dataset-item__z">{ds.n_z_candidates?.toLocaleString()} Z</span>
          </div>
          <div className="dataset-item__desc">{ds.desc}</div>
          {ds.id === activeId && <div className="dataset-item__active-dot" />}
        </div>
      ))}
    </div>
  );
}