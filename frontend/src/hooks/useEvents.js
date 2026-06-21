import { useState, useCallback, useMemo } from "react";
import { MOCK_EVENTS, MOCK_STATS } from "../constants/mock";

export const API_BASE = "http://localhost:8000";
const PAGE_SIZE = 20;

export function useEvents() {
  //  Events
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [zOnly, setZOnly] = useState(false);

  //  Datasets
  const [allDatasets, setAllDatasets] = useState([]);
  const [activeDatasetId, setActiveDatasetId] = useState(null);
  const [dsLoading, setDsLoading] = useState(false);
  const [dsError, setDsError] = useState(null);
  const [query, setQuery] = useState("");
  const [globalConfig, setGlobalConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(false);

  //Fetch config
  const fetchGlobalConfig = useCallback(async () => {
    setConfigLoading(true);
    try {
      const res = await fetch(`${API_BASE}/config`, { signal: AbortSignal.timeout(4000) });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setGlobalConfig(data);
    } catch (err) {
      console.error("Impossibile recuperare la configurazione globale:", err);
    }
    setConfigLoading(false);
  }, []);

  //  Fetch datasets
  const fetchDatasets = useCallback(async () => {
    setDsLoading(true);
    setDsError(null);
    try {
      const res = await fetch(`${API_BASE}/datasets`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setAllDatasets(data);
      if (data.length > 0) {
        setActiveDatasetId((prev) => prev ?? data[0].id);
      }
    } catch {
      setDsError("Could not load datasets from backend.");
    }
    setDsLoading(false);
  }, []);

  //  Filtered datasets (client-side)
  const datasets = useMemo(() => {
    if (!query.trim()) return allDatasets;
    const q = query.toLowerCase();
    return allDatasets.filter(
      (ds) =>
        ds.label.toLowerCase().includes(q) ||
        ds.energy.toLowerCase().includes(q) ||
        String(ds.year).includes(q) ||
        ds.dataset.toLowerCase().includes(q),
    );
  }, [allDatasets, query]);

  //  Fetch events
  const fetchEvents = useCallback(
    async (targetPage = 0, zOnlyFlag = false, datasetId = null) => {
      setLoading(true);
      try {
        const p = new URLSearchParams({
          limit: PAGE_SIZE,
          offset: targetPage * PAGE_SIZE,
        });
        if (zOnlyFlag) p.set("z_candidate", "true");
        if (datasetId) p.set("run_id", datasetId);

        const res = await fetch(`${API_BASE}/events?${p}`, {
          signal: AbortSignal.timeout(4000),
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        setEvents(data);
        setHasMore(data.length === PAGE_SIZE);
        setPage(targetPage);
        setDemoMode(false);
      } catch {
        setEvents(MOCK_EVENTS);
        setHasMore(false);
        setPage(0);
        setDemoMode(true);
      }
      setLoading(false);
    },
    [],
  );

  //  Fetch stats
  const fetchStats = useCallback(async (datasetId = null, onFailure = null) => {
    try {
      const p = new URLSearchParams();
      if (datasetId) p.set("dataset_id", datasetId);

      // Nota: verifica se il tuo endpoint è sotto "/analysis/stats" o solo "/stats"
      // a seconda di come hai configurato APIRouter(prefix="/analysis") nel backend
      const url = `${API_BASE}/stats${p.toString() ? `?${p}` : ""}`;

      const res = await fetch(url, { signal: AbortSignal.timeout(4000) });
      if (!res.ok) throw new Error();
      setStats(await res.json());
    } catch {
      setStats(MOCK_STATS);
      onFailure?.();
    }
  }, []);

  const goToPage = useCallback(
    (n) => fetchEvents(n, zOnly, activeDatasetId),
    [fetchEvents, zOnly, activeDatasetId],
  );
  const nextPage = useCallback(
    () => fetchEvents(page + 1, zOnly, activeDatasetId),
    [fetchEvents, page, zOnly, activeDatasetId],
  );
  const prevPage = useCallback(
    () => fetchEvents(page - 1, zOnly, activeDatasetId),
    [fetchEvents, page, zOnly, activeDatasetId],
  );
  const toggleZOnly = useCallback(
    (val) => {
      setZOnly(val);
      fetchEvents(0, val, activeDatasetId);
    },
    [fetchEvents, activeDatasetId],
  );

  return {
    // events
    events,
    stats,
    loading,
    demoMode,
    setDemoMode,
    page,
    hasMore,
    zOnly,
    fetchEvents,
    fetchStats,
    goToPage,
    nextPage,
    prevPage,
    toggleZOnly,
    // datasets
    datasets,
    activeDatasetId,
    setActiveDatasetId,
    dsLoading,
    dsError,
    query,
    setQuery,
    fetchDatasets,
    //config
    fetchGlobalConfig,
    globalConfig,
    configLoading
  };
}
