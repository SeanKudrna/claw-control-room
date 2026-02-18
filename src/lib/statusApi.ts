import type { StatusPayload } from '../types/status';

const FALLBACK_PATH = 'data/status.json';
const SOURCE_CONFIG_PATH = 'data/source.json';

type StatusFetchErrorCode =
  | 'status-http-error'
  | 'status-network-error'
  | 'status-payload-invalid'
  | 'status-url-unavailable';

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

async function resolveStatusUrl(signal?: AbortSignal): Promise<string> {
  try {
    const configUrl = withCacheBust(resolveBasePath(SOURCE_CONFIG_PATH));
    const cfgRes = await fetch(configUrl, { signal });
    if (cfgRes.ok) {
      const cfg = (await cfgRes.json()) as { url?: string };
      if (cfg.url && cfg.url.trim()) {
        return withCacheBust(cfg.url.trim());
      }
    }
  } catch {
    // Use fallback below.
  }

  const fallbackUrl = withCacheBust(resolveBasePath(FALLBACK_PATH));
  if (!fallbackUrl) {
    throw new StatusFetchError('status-url-unavailable', 'No status source URL could be resolved');
  }
  return fallbackUrl;
}

export async function fetchStatus(options?: { signal?: AbortSignal }): Promise<StatusPayload> {
  const statusUrl = await resolveStatusUrl(options?.signal);

  let response: Response;
  try {
    response = await fetch(statusUrl, { signal: options?.signal });
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
