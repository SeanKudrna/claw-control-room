import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchStatus, StatusFetchError } from '../lib/statusApi';
import type { StatusPayload } from '../types/status';

type FreshnessLevel = 'fresh' | 'aging' | 'stale';
type RefreshOutcome = 'idle' | 'success' | 'error';
type RefreshErrorCode =
  | 'status-http-error'
  | 'status-network-error'
  | 'status-payload-invalid'
  | 'status-url-unavailable'
  | 'unknown-status-error';

interface UseStatusResult {
  data: StatusPayload | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  errorCode: RefreshErrorCode | null;
  refresh: () => Promise<void>;
  lastRefreshAtMs: number | null;
  lastUpdatedLabel: string;
  freshnessLevel: FreshnessLevel;
  freshnessLabel: string;
  refreshOutcome: RefreshOutcome;
  sourceMode: 'configured' | 'fallback';
  sourceLabel: string;
  sourceDetail: string;
  liveStatusUrl: string | null;
  freshnessAgeMinutes: number | null;
  lastErrorCode: RefreshErrorCode | null;
  lastErrorMessage: string | null;
}

export function useStatus(refreshMs = 60_000): UseStatusResult {
  const [data, setData] = useState<StatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshAtMs, setLastRefreshAtMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<RefreshErrorCode | null>(null);
  const [refreshOutcome, setRefreshOutcome] = useState<RefreshOutcome>('idle');
  const [sourceMode, setSourceMode] = useState<'configured' | 'fallback'>('fallback');
  const [sourceLabel, setSourceLabel] = useState<string>('Fallback snapshot');
  const [sourceDetail, setSourceDetail] = useState<string>('Using local fallback snapshot.');
  const [liveStatusUrl, setLiveStatusUrl] = useState<string | null>(null);
  const [lastErrorCode, setLastErrorCode] = useState<RefreshErrorCode | null>(null);
  const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  const requestSeqRef = useRef(0);
  const activeControllerRef = useRef<AbortController | null>(null);

  const refresh = async () => {
    const requestSeq = requestSeqRef.current + 1;
    requestSeqRef.current = requestSeq;

    activeControllerRef.current?.abort();
    const controller = new AbortController();
    activeControllerRef.current = controller;

    try {
      if (!data) {
        setLoading(true);
      }
      setRefreshing(true);
      setError(null);
      setErrorCode(null);
      const next = await fetchStatus({ signal: controller.signal });

      if (requestSeq !== requestSeqRef.current) return;

      setData(next.payload);
      setSourceMode(next.source.mode);
      setSourceLabel(next.source.label);
      setSourceDetail(next.source.detail);
      setLiveStatusUrl(next.source.liveStatusUrl);
      setLastRefreshAtMs(Date.now());
      setRefreshOutcome('success');
    } catch (err) {
      if (controller.signal.aborted || requestSeq !== requestSeqRef.current) return;

      if (err instanceof StatusFetchError) {
        setErrorCode(err.code);
        setError(err.message);
        setLastErrorCode(err.code);
        setLastErrorMessage(err.message);
      } else {
        const unknownMessage = err instanceof Error ? err.message : 'Unknown status error';
        setErrorCode('unknown-status-error');
        setError(unknownMessage);
        setLastErrorCode('unknown-status-error');
        setLastErrorMessage(unknownMessage);
      }

      setRefreshOutcome('error');
    } finally {
      if (requestSeq === requestSeqRef.current) {
        setRefreshing(false);
        setLoading(false);
      }
      if (activeControllerRef.current === controller) {
        activeControllerRef.current = null;
      }
    }
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, refreshMs);
    return () => {
      window.clearInterval(timer);
      activeControllerRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshMs]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const lastUpdatedLabel = useMemo(() => {
    if (!data?.generatedAtLocal) return 'n/a';
    return data.generatedAtLocal;
  }, [data?.generatedAtLocal]);

  const freshness = useMemo(() => {
    if (!data?.generatedAt) {
      return { level: 'stale' as FreshnessLevel, label: 'Freshness unknown', ageMinutes: null as number | null };
    }

    const generatedAtMs = Date.parse(data.generatedAt);
    if (!Number.isFinite(generatedAtMs)) {
      return { level: 'stale' as FreshnessLevel, label: 'Freshness unknown', ageMinutes: null as number | null };
    }

    const ageMinutes = Math.max(0, Math.floor((nowMs - generatedAtMs) / 60_000));
    if (ageMinutes <= 5) {
      return { level: 'fresh' as FreshnessLevel, label: `Fresh (${ageMinutes}m old)`, ageMinutes };
    }
    if (ageMinutes <= 15) {
      return { level: 'aging' as FreshnessLevel, label: `Aging (${ageMinutes}m old)`, ageMinutes };
    }
    return { level: 'stale' as FreshnessLevel, label: `Stale (${ageMinutes}m old)`, ageMinutes };
  }, [data?.generatedAt, nowMs]);

  return {
    data,
    loading,
    refreshing,
    error,
    errorCode,
    refresh,
    lastRefreshAtMs,
    lastUpdatedLabel,
    freshnessLevel: freshness.level,
    freshnessLabel: freshness.label,
    refreshOutcome,
    sourceMode,
    sourceLabel,
    sourceDetail,
    liveStatusUrl,
    freshnessAgeMinutes: freshness.ageMinutes,
    lastErrorCode,
    lastErrorMessage,
  };
}
