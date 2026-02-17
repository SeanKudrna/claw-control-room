import { useEffect, useMemo, useState } from 'react';
import { fetchStatus } from '../lib/statusApi';
import type { StatusPayload } from '../types/status';

interface UseStatusResult {
  data: StatusPayload | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastUpdatedLabel: string;
}

export function useStatus(refreshMs = 60_000): UseStatusResult {
  const [data, setData] = useState<StatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setError(null);
      const next = await fetchStatus();
      setData(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown status error');
    } finally {
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

  return { data, loading, error, refresh, lastUpdatedLabel };
}
