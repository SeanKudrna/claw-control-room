import type { StatusPayload } from '../types/status';

const FALLBACK_PATH = 'data/status.json';
const SOURCE_CONFIG_PATH = 'data/source.json';

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
    if (!cfgRes.ok) throw new Error('source config unavailable');

    const cfg = (await cfgRes.json()) as { url?: string };
    if (cfg.url && cfg.url.trim()) {
      return withCacheBust(cfg.url.trim());
    }
  } catch {
    // Use fallback below.
  }

  return withCacheBust(resolveBasePath(FALLBACK_PATH));
}

export async function fetchStatus(options?: { signal?: AbortSignal }): Promise<StatusPayload> {
  const statusUrl = await resolveStatusUrl(options?.signal);
  const response = await fetch(statusUrl, { signal: options?.signal });
  if (!response.ok) {
    throw new Error(`Status fetch failed: ${response.status}`);
  }
  return (await response.json()) as StatusPayload;
}
