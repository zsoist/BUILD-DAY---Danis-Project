#!/usr/bin/env python3
"""Exporta runs/*/swarm.jsonl → dashboard/feed.json (modo local del dashboard).

Uso:  python3 scripts/feed.py            # una vez
      python3 scripts/feed.py --beam     # además sube a Supabase (backfill)
      python3 scripts/feed.py --watch    # re-exporta cada 2s

OJO: --beam NO es idempotente (inserta todo de nuevo). Antes de re-beamear,
truncar army_events en Supabase o habrá eventos duplicados.
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def env():
    d = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def export():
    rows, i = [], 0
    for jl in sorted(ROOT.glob("runs/*/swarm.jsonl")):
        run_id = jl.parent.name
        # corridas viejas sin "t": sintetizar desde el nombre (YYYYmmdd-HHMMSS)
        try:
            base = datetime.strptime(run_id[:15], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            base = datetime.now(timezone.utc)
        for n, line in enumerate(jl.read_text().splitlines()):
            try:
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            i += 1
            secs = p["t"] if "t" in p else base.timestamp() + n * 4
            ts = datetime.fromtimestamp(secs, tz=timezone.utc)
            rows.append({"id": i, "run_id": run_id, "ts": ts.isoformat(),
                         "event": p.get("event"), "task_id": p.get("id"),
                         "payload": p})
    out = ROOT / "dashboard" / "feed.json"
    out.write_text(json.dumps(rows, ensure_ascii=False))
    print(f"feed.json: {len(rows)} eventos de {len(set(r['run_id'] for r in rows))} corridas")
    return rows


def beam(rows):
    e = env()
    url, key = e["SUPABASE_URL"], e["SUPABASE_PUBLISHABLE_KEY"]
    body = json.dumps([{k: r[k] for k in ("run_id", "ts", "event", "task_id", "payload")}
                       for r in rows]).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/army_events", data=body, method="POST",
        headers={"apikey": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Supabase: backfill {r.status}")


if __name__ == "__main__":
    rows = export()
    if "--beam" in sys.argv:
        beam(rows)
    while "--watch" in sys.argv:
        time.sleep(2)
        export()
