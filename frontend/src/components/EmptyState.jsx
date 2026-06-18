import "../styles/panels.css";

export function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-state__ring">
        <div className="empty-state__inner" />
      </div>
      <p className="empty-state__text">Select a collision event<br />to visualize</p>
    </div>
  );
}