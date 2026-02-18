import type { StatusPayload } from '../types/status';

const FALLBACK_PATH = 'data/status.json';
const SOURCE_CONFIG_PATH = 'data/source.json';

type StatusFetchErrorCode =
  | 'status-http-error'
  | 'status-network-error'
  | 'status-payload-invalid'
  | 'status-url-unavailable';

export interface StatusFetchResult {
  payload: StatusPayload;
  source: {
    mode: 'configured' | 'fallback';
    label: string;
    detail: string;
  };
}

export class StatusFetchError extends Error {
  code: StatusFetchErrorCode;
  status?: number;

  constructor(code: StatusFetchErrorCode, message: string, options?: { status?: number }) {
    super(message);
    this.code = code;
    this.status = options?.status;
    this.name = 'StatusFetchError';
  }
}

function withCacheBust(url: string): string {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}ts=${Date.now()}`;
}

function resolveBasePath(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  const base = import.meta.env.BASE_URL ?? '/';
  return `${base}${path}`.replace(/\/\//g, '/').replace('http:/', 'http://').replace('https:/', 'https://');
}

async function resolveStatusUrls(signal?: AbortSignal): Promise<{
  configuredUrl: string | null;
  fallbackUrl: string;
  configStatus: 'configured' | 'missing' | 'unreachable';
}> {
  const fallbackUrl = withCacheBust(resolveBasePath(FALLBACK_PATH));
  if (!fallbackUrl) {
    throw new StatusFetchError('status-url-unavailable', 'No status source URL could be resolved');
  }

  try {
    const configUrl = withCacheBust(resolveBasePath(SOURCE_CONFIG_PATH));
    const cfgRes = await fetch(configUrl, { signal });
    if (!cfgRes.ok) {
      return {
        configuredUrl: null,
        fallbackUrl,
        configStatus: 'unreachable',
      };
    }

    const cfg = (await cfgRes.json()) as { url?: string };
    const configured = cfg.url?.trim();
    if (configured) {
      return {
        configuredUrl: withCacheBust(configured),
        fallbackUrl,
        configStatus: 'configured',
      };
    }

    return {
      configuredUrl: null,
      fallbackUrl,
      configStatus: 'missing',
    };
  } catch {
    return {
      configuredUrl: null,
      fallbackUrl,
      configStatus: 'unreachable',
    };
  }
}

async function fetchStatusPayload(url: string, signal?: AbortSignal): Promise<StatusPayload> {
  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch {
    throw new StatusFetchError('status-network-error', 'Status endpoint could not be reached');
  }

  if (!response.ok) {
    throw new StatusFetchError('status-http-error', `Status endpoint returned ${response.status}`, {
      status: response.status,
    });
  }

  try {
    return (await response.json()) as StatusPayload;
  } catch {
    throw new StatusFetchError('status-payload-invalid', 'Status payload is not valid JSON');
  }
}

export async function fetchStatus(options?: { signal?: AbortSignal }): Promise<StatusFetchResult> {
  const resolved = await resolveStatusUrls(options?.signal);

  if (resolved.configuredUrl) {
    try {
      const payload = await fetchStatusPayload(resolved.configuredUrl, options?.signal);
      return {
        payload,
        source: {
          mode: 'configured',
          label: 'Live source',
          detail: 'Using configured status source (gist/live feed).',
        },
      };
    } catch (primaryError) {
      const payload = await fetchStatusPayload(resolved.fallbackUrl, options?.signal);
      const primaryCode = primaryError instanceof StatusFetchError ? primaryError.code : 'status-network-error';
      return {
        payload,
        source: {
          mode: 'fallback',
          label: 'Fallback snapshot',
          detail: `Primary source failed (${primaryCode}); using local fallback snapshot.`,
        },
      };
    }
  }

  const payload = await fetchStatusPayload(resolved.fallbackUrl, options?.signal);
  return {
    payload,
    source: {
      mode: 'fallback',
      label: 'Fallback snapshot',
      detail:
        resolved.configStatus === 'unreachable'
          ? 'Source config unavailable; using local fallback snapshot.'
          : 'No configured source URL; using local fallback snapshot.',
    },
  };
}
