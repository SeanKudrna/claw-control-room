#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
from pathlib import Path

BLOCK_RE = re.compile(r"^###\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s+—\s+(.+)$")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_daily_plan(text: str):
    timeline = []
    for line in text.splitlines():
        m = BLOCK_RE.match(line.strip())
        if m:
            timeline.append({"time": f"{m.group(1)}-{m.group(2)}", "task": m.group(3)})
    return timeline


def parse_today_status(text: str):
    focus = ""
    active = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- Primary focus:"):
            focus = s.replace("- Primary focus:", "").strip()
        if s.startswith("- Running now:"):
            active = s.replace("- Running now:", "").strip()
    return focus, active


def get_reliability(workspace: Path):
    # Try live report script first
    script = workspace / "scripts" / "reliability_watchdog_report.py"
    if script.exists():
        import subprocess
        try:
            out = subprocess.check_output([
                "python3", str(script), "--window-hours", "8", "--json"
            ], text=True, timeout=30)
            data = json.loads(out)
            return {"status": data.get("health", {}).get("status", "unknown")}
        except Exception:
            pass
    return {"status": "unknown"}


def get_next_jobs(cron_jobs_path: Path, limit=8):
    doc = json.loads(read(cron_jobs_path) or "{}")
    jobs = [j for j in doc.get("jobs", []) if j.get("enabled")]
    jobs.sort(key=lambda j: (j.get("state", {}).get("nextRunAtMs") or 2**63))

    out = []
    for j in jobs[:limit]:
        nxt = j.get("state", {}).get("nextRunAtMs")
        nxt_str = "n/a"
        if isinstance(nxt, int):
            nxt_str = dt.datetime.fromtimestamp(nxt/1000, dt.timezone.utc).astimezone().strftime("%H:%M")
        out.append({
            "name": j.get("name", ""),
            "nextRun": nxt_str,
            "lastStatus": j.get("state", {}).get("lastStatus")
        })
    return out


def recent_findings(memory_text: str, limit=6):
    lines = [l.strip() for l in memory_text.splitlines() if l.strip().startswith("-")]
    return [l.lstrip("- ") for l in lines[-limit:]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", default="/Users/seankudrna/.openclaw/workspace")
    p.add_argument("--out", default="/Users/seankudrna/.openclaw/workspace/claw-control-room/data/status.json")
    args = p.parse_args()

    workspace = Path(args.workspace)
    out = Path(args.out)

    daily_plan = read(workspace / "DAILY_PLAN.md")
    today_status = read(workspace / "TODAY_STATUS.md")
    memory_today = read(workspace / "memory" / f"{dt.datetime.now().strftime('%Y-%m-%d')}.md")

    focus, active = parse_today_status(today_status)

    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generatedAtLocal": dt.datetime.now().strftime("%Y-%m-%d %H:%M %Z"),
        "currentFocus": focus,
        "activeWork": active,
        "reliability": get_reliability(workspace),
        "timeline": parse_daily_plan(daily_plan),
        "nextJobs": get_next_jobs(Path("/Users/seankudrna/.openclaw/cron/jobs.json")),
        "findings": recent_findings(memory_today),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
