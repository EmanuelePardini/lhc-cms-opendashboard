import "../../styles/panels.css";

export function Header({ demoMode }) {
  return (
    <div className="panel panel--header">
      <div className="header__title">CMS Open Data · Dimuon Events</div>
      <div className="header__sub">
        Large Hadron Collider — CERN, Geneva{demoMode ? " · DEMO MODE" : ""}
      </div>
    </div>
  );
}