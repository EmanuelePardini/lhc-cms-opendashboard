import { useState, useEffect }  from "react";
import { useEvents }            from "./hooks/useEvents";
import { SceneCanvas }          from "./components/SceneCanvas";
import { EmptyState }           from "./components/EmptyState";
import { Header }               from "./components/panels/Header";
import { DatasetSelector }      from "./components/panels/DatasetSelector";
import { EventSelector }        from "./components/panels/EventSelector";
import { EventInfo }            from "./components/panels/EventInfo";
import { Legend }               from "./components/panels/Legend";
import { StatsBar }             from "./components/panels/StatsBar";
import { ControlsHint }         from "./components/panels/ControlsHint";
import { DraggablePanel }       from "./components/DraggablePanel";
import { PipelineConfig }       from "./components/panels/PipelineConfig";

export default function LHCViewer() {
  const [selected, setSelected] = useState(null);

  const {
    events, stats, loading, demoMode, setDemoMode,
    page, hasMore, zOnly,
    fetchEvents, fetchStats,
    nextPage, prevPage, toggleZOnly,
    datasets, activeDatasetId, setActiveDatasetId,
    dsLoading, dsError,
    query, setQuery,
    fetchDatasets, globalConfig,
    configLoading,
    fetchGlobalConfig
  } = useEvents();

  useEffect(() => {
    fetchDatasets();
    fetchGlobalConfig();
    fetchStats();
  }, [fetchDatasets, fetchStats, fetchGlobalConfig]);

  useEffect(() => {
    if (activeDatasetId === null) return;
    setSelected(null);
    fetchEvents(0, zOnly, activeDatasetId);
    fetchStats(activeDatasetId);
    fetchGlobalConfig();
  }, [activeDatasetId]);

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative", overflow: "hidden", background: "radial-gradient(ellipse at 50% 50%, #0a1628 0%, #050a14 70%)" }}>
      <SceneCanvas  event={selected} />
      {!selected && <EmptyState />}

      <Header demoMode={demoMode} />

      <DraggablePanel id="datasets" title="Dataset" initialPos={{ x: 20, y: 76 }}>
        <DatasetSelector
          datasets={datasets}
          activeId={activeDatasetId}
          loading={dsLoading}
          error={dsError}
          query={query}
          onQueryChange={setQuery}
          onSelect={id => setActiveDatasetId(id)}
        />
      </DraggablePanel>

      <DraggablePanel id="events" title="Collision Events" initialPos={{ x: 300, y: 76 }}>
        <EventSelector
          events={events}
          selected={selected}
          loading={loading}
          page={page}
          hasMore={hasMore}
          zOnly={zOnly}
          onSelect={setSelected}
          onRefresh={(p, z) => fetchEvents(p, z, activeDatasetId)}
          onNext={nextPage}
          onPrev={prevPage}
          onToggleZOnly={toggleZOnly}
        />
      </DraggablePanel>

      <DraggablePanel id="info" title="Event Details" initialPos={{ x: window.innerWidth - 300, y: 76 }}>
        <EventInfo event={selected} />
      </DraggablePanel>

      <DraggablePanel id="legend" title="Legend" initialPos={{ x: window.innerWidth - 300, y: 420 }} defaultOpen={true}>
        <Legend />
      </DraggablePanel>

      <DraggablePanel id="controls" title="Controls" initialPos={{ x: 20, y: window.innerHeight - 160 }} defaultOpen={true}>
        <ControlsHint />
      </DraggablePanel>

      <DraggablePanel id="stats" title="Statistics" initialPos={{ x: Math.round(window.innerWidth / 2) - 230, y: window.innerHeight - 120 }}>
        <StatsBar stats={stats} />
      </DraggablePanel>

      <DraggablePanel id="pipeline-config" title="Filters Configuration" initialPos={{ x: 20, y: 260 }} defaultOpen={true}>
        <PipelineConfig config={globalConfig} loading={configLoading} />
      </DraggablePanel>
    </div>
  );
}