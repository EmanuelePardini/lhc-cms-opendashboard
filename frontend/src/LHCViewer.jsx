import { useState, useEffect }   from "react";
import { useEvents }             from "./hooks/useEvents";
import { SceneCanvas }           from "./components/SceneCanvas";
import { EmptyState }            from "./components/EmptyState";
import { Header }                from "./components/panels/Header";
import { EventSelector }         from "./components/panels/EventSelector";
import { EventInfo }             from "./components/panels/EventInfo";
import { Legend }                from "./components/panels/Legend";
import { StatsBar }              from "./components/panels/StatsBar";
import { ControlsHint }         from "./components/panels/ControlsHint";

export default function LHCViewer() {
  const [selected, setSelected] = useState(null);
  const {
    events, stats, loading, demoMode, setDemoMode,
    page, hasMore, zOnly,
    fetchEvents, fetchStats,
    nextPage, prevPage, toggleZOnly,
  } = useEvents();

  useEffect(() => {
    fetchEvents(0, false);
    fetchStats(() => setDemoMode(true));
  }, [fetchEvents, fetchStats]);

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative", overflow: "hidden", background: "radial-gradient(ellipse at 50% 50%, #0a1628 0%, #050a14 70%)" }}>
      <SceneCanvas   event={selected} />
      {!selected && <EmptyState />}
      <Header        demoMode={demoMode} />
      <EventSelector
        events={events}
        selected={selected}
        loading={loading}
        page={page}
        hasMore={hasMore}
        zOnly={zOnly}
        onSelect={setSelected}
        onRefresh={fetchEvents}
        onNext={nextPage}
        onPrev={prevPage}
        onToggleZOnly={toggleZOnly}
      />
      <EventInfo     event={selected} />
      <Legend />
      <ControlsHint />
      <StatsBar      stats={stats} />
    </div>
  );
}