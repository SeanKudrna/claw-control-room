import { useEffect, useMemo, useState } from 'react';
import { fetchStatus } from '../lib/statusApi';
import type { StatusPayload } from '../types/status';

type FreshnessLevel = 'fresh' | 'aging' | 'stale';

interface UseStatusResult {
  data: StatusPayload | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastRefreshAtMs: number | null;
  lastUpdatedLabel: string;
  freshnessLevel: FreshnessLevel;
  freshnessLabel: string;
}

export function useStatus(refreshMs = 60_000): UseStatusResult {
  const [data, setData] = useState<StatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshAtMs, setLastRefreshAtMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      if (!data) {
        setLoading(true);
      }
      setRefreshing(true);
      setError(null);
      const next = await fetchStatus();
      setData(next);
      setLastRefreshAtMs(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown status error');
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, refreshMs);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshMs]);

  const lastUpdatedLabel = useMemo(() => {
    if (!data?.generatedAtLocal) return 'n/a';
    return data.generatedAtLocal;
  }, [data?.generatedAtLocal]);

  const freshness = useMemo(() => {
    if (!data?.generatedAt) {
      return { level: 'stale' as FreshnessLevel, label: 'Freshness unknown' };
    }

    const generatedAtMs = Date.parse(data.generatedAt);
    if (!Number.isFinite(generatedAtMs)) {
      return { level: 'stale' as FreshnessLevel, label: 'Freshness unknown' };
    }

    const ageMinutes = Math.max(0, Math.floor((Date.now() - generatedAtMs) / 60_000));
    if (ageMinutes <= 5) {
      return { level: 'fresh' as FreshnessLevel, label: `Fresh (${ageMinutes}m old)` };
    }
    if (ageMinutes <= 15) {
      return { level: 'aging' as FreshnessLevel, label: `Aging (${ageMinutes}m old)` };
    }
    return { level: 'stale' as FreshnessLevel, label: `Stale (${ageMinutes}m old)` };
  }, [data?.generatedAt]);

  return {
    data,
    loading,
    refreshing,
    error,
    refresh,
    lastRefreshAtMs,
    lastUpdatedLabel,
    freshnessLevel: freshness.level,
    freshnessLabel: freshness.label,
  };
}
