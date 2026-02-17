const DEFAULT_STATUS_URL = 'data/status.json';

async function resolveStatusUrl() {
  try {
    const cfgRes = await fetch('data/source.json?ts=' + Date.now());
    if (!cfgRes.ok) return DEFAULT_STATUS_URL;
    const cfg = await cfgRes.json();
    if (cfg && typeof cfg.url === 'string' && cfg.url.trim()) {
      return cfg.url.trim() + (cfg.url.includes('?') ? '&' : '?') + 'ts=' + Date.now();
    }
  } catch (_) {
    // fall through to local default
  }
  return DEFAULT_STATUS_URL + '?ts=' + Date.now();
}

async function load() {
  const statusUrl = await resolveStatusUrl();
  const res = await fetch(statusUrl);
  const data = await res.json();

  document.getElementById('generatedAt').textContent = `Updated ${data.generatedAtLocal}`;
  document.getElementById('currentFocus').textContent = data.currentFocus || 'n/a';
  document.getElementById('activeWork').textContent = data.activeWork || 'No active task';

  const hb = document.getElementById('healthBadge');
  hb.textContent = (data.reliability?.status || 'unknown').toUpperCase();
  hb.className = 'badge ' + (data.reliability?.status || '');

  const timeline = document.getElementById('timeline');
  timeline.innerHTML = '';
  (data.timeline || []).forEach(item => {
    const li = document.createElement('li');
    li.textContent = `${item.time} — ${item.task}`;
    timeline.appendChild(li);
  });

  const jobs = document.getElementById('jobsTable');
  jobs.innerHTML = '';
  (data.nextJobs || []).forEach(job => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${job.nextRun}</td><td>${job.name}</td><td>${job.lastStatus || 'n/a'}</td>`;
    jobs.appendChild(tr);
  });

  const findings = document.getElementById('findings');
  findings.innerHTML = '';
  (data.findings || []).forEach(f => {
    const li = document.createElement('li');
    li.textContent = f;
    findings.appendChild(li);
  });
}

load().catch(err => {
  document.getElementById('generatedAt').textContent = 'Failed to load status source';
  console.error(err);
});
