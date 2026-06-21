import "../../styles/panels.css";

export function Header({ demoMode }) {
  return (
    <>
      <div className="panel panel--header">
        <div className="header__title">CMS Open Data · Dimuon Events</div>
        <div className="header__sub">
          Large Hadron Collider {demoMode ? " · DEMO MODE" : ""}
        </div>
      </div>

      {demoMode && (
        <div className="panel panel--demo-warning">
          <span className="demo-warning__icon">⚠</span>
          <span className="demo-warning__text">
            Backend unreachable — data shown are <b>template examples</b>, not real events.
          </span>
        </div>
      )}
    </>
  );
}