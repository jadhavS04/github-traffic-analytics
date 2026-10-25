#!/usr/bin/env python3
"""Turn data/*.csv into docs/data.js (loaded by docs/index.html)."""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import TABLES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0


def main():
    out = {}
    for name, spec in TABLES.items():
        if name == "runs":
            continue
        rows, p = [], ROOT / "data" / f"{name}.csv"
        if p.exists():
            with p.open(newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append([num(r[c]) if c in spec["num"] else r[c] for c in spec["cols"]])
        out[name] = {"cols": spec["cols"], "rows": rows}
    owners = [r[0].split("/")[0] for r in out["repo_stats"]["rows"]]
    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "owner": max(set(owners), key=owners.count) if owners else "",
        "tables": out,
    }
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "data.js").write_text("window.TRAFFIC=" + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"docs/data.js written ({sum(len(t['rows']) for t in out.values())} rows)")


if __name__ == "__main__":
    main()
