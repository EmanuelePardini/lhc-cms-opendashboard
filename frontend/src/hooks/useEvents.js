import { useState, useCallback } from "react";
import { MOCK_EVENTS, MOCK_STATS } from "../constants/mock";

const API_BASE   = "http://localhost:8000";
const PAGE_SIZE  = 20;

export function useEvents() {
  const [events,    setEvents]    = useState([]);
  const [stats,     setStats]     = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [demoMode,  setDemoMode]  = useState(false);
  const [page,      setPage]      = useState(0);
  const [hasMore,   setHasMore]   = useState(true);
  const [zOnly,     setZOnly]     = useState(false);

  const fetchEvents = useCallback(async (targetPage = 0, zOnlyFlag = false) => {
    setLoading(true);
    try {
      const p = new URLSearchParams({
        limit:  PAGE_SIZE,
        offset: targetPage * PAGE_SIZE,
      });
      if (zOnlyFlag) p.set("z_candidate", "true");

      const res = await fetch(`${API_BASE}/events?${p}`, { signal: AbortSignal.timeout(4000) });
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
  }, []);

  const fetchStats = useCallback(async (onFailure) => {
    try {
      const res = await fetch(`${API_BASE}/analysis/stats`, { signal: AbortSignal.timeout(4000) });
      if (!res.ok) throw new Error();
      setStats(await res.json());
    } catch {
      setStats(MOCK_STATS);
      onFailure?.();
    }
  }, []);

  const goToPage   = useCallback((n) => fetchEvents(n, zOnly),   [fetchEvents, zOnly]);
  const nextPage   = useCallback(() => fetchEvents(page + 1, zOnly), [fetchEvents, page, zOnly]);
  const prevPage   = useCallback(() => fetchEvents(page - 1, zOnly), [fetchEvents, page, zOnly]);
  const toggleZOnly = useCallback((val) => {
    setZOnly(val);
    fetchEvents(0, val);
  }, [fetchEvents]);

  return {
    events, stats, loading, demoMode, setDemoMode,
    page, hasMore, zOnly,
    fetchEvents, fetchStats,
    goToPage, nextPage, prevPage, toggleZOnly,
  };
}