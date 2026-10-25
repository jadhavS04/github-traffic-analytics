#!/usr/bin/env python3
"""Collect GitHub traffic + repo analytics and merge them into data/*.csv.

GitHub only keeps 14 days of views/clones. Run this daily: every day in the
window is written with its latest value (same date => overwritten), and days
that are new get appended, so history grows forever.

Usage:
    GH_TOKEN=ghp_xxx python scripts/collect.py          # collect
    GH_TOKEN=ghp_xxx python scripts/collect.py --check  # diagnose token/permissions
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema import TABLES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = ROOT / "config.json"
API = "https://api.github.com"
WINDOW = 14  # days GitHub keeps for views/clones

SESSION = requests.Session()


class ApiError(Exception):
    def __init__(self, status: int, url: str, message: str = ""):
        super().__init__(f"HTTP {status} for {url}: {message}")
        self.status = status


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------- HTTP
def request(url, params=None, headers=None, ok=(200,), retries=4):
    full = url if url.startswith("http") else API + url
    last = ApiError(0, full, "request failed")
    for attempt in range(retries):
        try:
            r = SESSION.get(full, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:
            last = ApiError(0, full, str(exc))
            time.sleep(2 ** attempt)
            continue
        if r.status_code in ok:
            return r
        if r.status_code in (403, 429):
            if r.headers.get("Retry-After"):
                time.sleep(min(int(r.headers["Retry-After"]) + 1, 120))
                continue
            if r.headers.get("X-RateLimit-Remaining") == "0":
                wait = max(int(r.headers.get("X-RateLimit-Reset", "0")) - int(time.time()), 1) + 1
                if wait > 900:
                    raise ApiError(r.status_code, full, "rate limit exhausted")
                print(f"  rate limited, sleeping {wait}s")
                time.sleep(wait)
                continue
        if r.status_code >= 500:
            last = ApiError(r.status_code, full, "server error")
            time.sleep(2 ** attempt)
            continue
        try:
            msg = r.json().get("message", "")
        except Exception:
            msg = ""
        raise ApiError(r.status_code, full, msg)
    raise last


def paginate(url, params=None, headers=None, max_pages=300):
    params = dict(params or {})
    params.setdefault("per_page", 100)
    out, r = [], request(url, params, headers)
    for _ in range(max_pages):
        data = r.json()
        if isinstance(data, list):
            out.extend(data)
        nxt = r.links.get("next", {}).get("url")
        if not nxt:
            break
        r = request(nxt, headers=headers)
    return out


def count_items(url, params=None):
    p = dict(params or {})
    p["per_page"] = 1
    r = request(url, p)
    last = r.links.get("last", {}).get("url")
    if last:
        return int(parse_qs(urlparse(last).query)["page"][0])
    data = r.json()
    return len(data) if isinstance(data, list) else 0


# -------------------------------------------------------------------- store
class Store:
    """CSV-backed tables. Same key => overwrite, new key => append."""

    def __init__(self):
        self.t: dict[str, dict[tuple, dict]] = {}

    def table(self, name):
        if name not in self.t:
            spec, rows = TABLES[name], {}
            p = DATA / f"{name}.csv"
            if p.exists():
                with p.open(newline="", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        key = tuple(row.get(k, "") for k in spec["key"])
                        rows[key] = {c: row.get(c, "") for c in spec["cols"]}
            self.t[name] = rows
        return self.t[name]

    def upsert(self, name, row):
        spec = TABLES[name]
        row = {c: ("" if row.get(c) is None else row.get(c, "")) for c in spec["cols"]}
        self.table(name)[tuple(str(row[k]) for k in spec["key"])] = row

    def has(self, name, key):
        return tuple(str(k) for k in key) in self.table(name)

    def replace(self, name, pred, rows):
        tbl = self.table(name)
        for k in [k for k, v in tbl.items() if pred(v)]:
            del tbl[k]
        for r in rows:
            self.upsert(name, r)

    def count(self, name, repo):
        return sum(1 for v in self.table(name).values() if v["repo"] == repo)

    def save(self):
        DATA.mkdir(parents=True, exist_ok=True)
        for name, spec in TABLES.items():
            rows = self.table(name)
            tmp = DATA / f"{name}.csv.tmp"
            with tmp.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=spec["cols"], lineterminator="\n")
                w.writeheader()
                for _, row in sorted(rows.items()):
                    w.writerow(row)
            tmp.replace(DATA / f"{name}.csv")


# ---------------------------------------------------------------- collectors
def collect_traffic(store, full, d):
    window = [(date.fromisoformat(d) - timedelta(days=i)).isoformat() for i in range(WINDOW)]
    for kind in ("views", "clones"):
        data = request(f"/repos/{full}/traffic/{kind}", {"per": "day"}).json()
        seen = set()
        for item in data.get(kind, []):
            day = item["timestamp"][:10]
            seen.add(day)
            store.upsert(kind, {"repo": full, "date": day, kind: item["count"], "uniques": item["uniques"]})
        # GitHub omits zero-traffic days; record them as real zeros (never over existing data)
        for day in window:
            if day not in seen and not store.has(kind, (full, day)):
                store.upsert(kind, {"repo": full, "date": day, kind: 0, "uniques": 0})

    refs = request(f"/repos/{full}/traffic/popular/referrers").json()
    store.replace("referrers", lambda r: r["repo"] == full and r["date"] == d,
                  [{"repo": full, "date": d, "referrer": x["referrer"], "count": x["count"], "uniques": x["uniques"]} for x in refs])
    paths = request(f"/repos/{full}/traffic/popular/paths").json()
    store.replace("paths", lambda r: r["repo"] == full and r["date"] == d,
                  [{"repo": full, "date": d, "path": x["path"], "title": x.get("title", ""), "count": x["count"], "uniques": x["uniques"]} for x in paths])


def collect_releases(store, full, d):
    rels = request(f"/repos/{full}/releases", {"per_page": 30}).json()
    rows = [{"repo": full, "date": d, "tag": rel["tag_name"], "asset": a["name"], "downloads": a["download_count"]}
            for rel in rels for a in (rel.get("assets") or [])]
    store.replace("releases", lambda r: r["repo"] == full and r["date"] == d, rows)


def collect_languages(store, full, d):
    langs = request(f"/repos/{full}/languages").json()
    store.replace("languages", lambda r: r["repo"] == full and r["date"] == d,
                  [{"repo": full, "date": d, "language": k, "bytes": v} for k, v in langs.items()])


def collect_commits(store, full, d):
    r = None
    for _ in range(4):  # GitHub returns 202 while it computes the stats
        r = request(f"/repos/{full}/stats/commit_activity", ok=(200, 202, 204))
        if r.status_code == 200:
            break
        time.sleep(3)
    if r is None or r.status_code != 200:
        return
    for wk in r.json():
        start = datetime.fromtimestamp(wk["week"], timezone.utc).date()
        for i, c in enumerate(wk["days"]):
            day = (start + timedelta(days=i)).isoformat()
            if c > 0 and day <= d:
                store.upsert("commits", {"repo": full, "date": day, "commits": c})


def collect_stargazers(store, full, meta, d):
    have, want = store.count("stargazers", full), meta.get("stargazers_count", 0)
    if have == want and (want == 0 or date.fromisoformat(d).weekday() != 0):
        return  # unchanged; full refresh every Monday to catch un-stars
    items = paginate(f"/repos/{full}/stargazers", headers={"Accept": "application/vnd.github.star+json"})
    store.replace("stargazers", lambda r: r["repo"] == full,
                  [{"repo": full, "user": (s.get("user") or {}).get("login", "ghost"), "starred_at": s["starred_at"]} for s in items])


def collect_forks(store, full, meta, d):
    have, want = store.count("forks", full), meta.get("forks_count", 0)
    if have == want and (want == 0 or date.fromisoformat(d).weekday() != 0):
        return
    items = paginate(f"/repos/{full}/forks", {"sort": "oldest"})
    store.replace("forks", lambda r: r["repo"] == full,
                  [{"repo": full, "fork": f["full_name"], "created_at": f["created_at"]} for f in items])


def collect_repo(store, full, d, cfg):
    """Returns (traffic_ok, [problems])."""
    problems = []
    meta = request(f"/repos/{full}").json()
    full = meta["full_name"]

    def safe(label, fn, *a):
        try:
            fn(*a)
            return True
        except ApiError as e:
            problems.append(f"{label}: {e}")
            return False

    prs = 0
    try:
        prs = count_items(f"/repos/{full}/pulls", {"state": "open"})
    except ApiError as e:
        problems.append(f"pulls: {e}")
    store.upsert("repo_stats", {
        "repo": full, "date": d, "stars": meta.get("stargazers_count", 0), "forks": meta.get("forks_count", 0),
        "watchers": meta.get("subscribers_count", 0), "open_issues": max(meta.get("open_issues_count", 0) - prs, 0),
        "open_prs": prs, "size_kb": meta.get("size", 0)})

    traffic_ok = safe("traffic", collect_traffic, store, full, d)
    safe("releases", collect_releases, store, full, d)
    safe("languages", collect_languages, store, full, d)
    safe("commits", collect_commits, store, full, d)
    if cfg.get("collect_stargazers", True):
        safe("stargazers", collect_stargazers, store, full, meta, d)
    if cfg.get("collect_forks", True):
        safe("forks", collect_forks, store, full, meta, d)
    return traffic_ok, problems


# ----------------------------------------------------------------- discovery
def discover(cfg, login):
    owner = cfg.get("owner") or login
    explicit = cfg.get("repos") or []
    if explicit:
        return [n if "/" in n else f"{owner}/{n}" for n in explicit]
    if owner.lower() == login.lower():
        repos = paginate("/user/repos", {"affiliation": "owner", "sort": "full_name"})
    else:
        repos = paginate(f"/users/{owner}/repos", {"type": "owner"})
    exclude = {e.lower() for e in cfg.get("exclude", [])}
    out = []
    for r in repos:
        if r["fork"] and not cfg.get("include_forks", False):
            continue
        if r["archived"] and not cfg.get("include_archived", False):
            continue
        if r["private"] and not cfg.get("include_private", False):
            continue
        if r["name"].lower() in exclude or r["full_name"].lower() in exclude:
            continue
        out.append(r["full_name"])
    return out


def check(repos, login, scopes):
    print(f"Authenticated as: {login}")
    print(f"Token scopes    : {scopes or '(fine-grained token: scopes not shown)'}")
    print(f"Repos selected  : {len(repos)}")
    if not repos:
        print("!! No repositories matched your config.json filters.")
        return 1
    full = repos[0]
    try:
        request(f"/repos/{full}/traffic/views")
        print(f"Traffic API     : OK on {full}")
        return 0
    except ApiError as e:
        print(f"Traffic API     : FAILED on {full} -> {e}")
        print("Fix: classic token needs the 'repo' scope; fine-grained token needs 'Administration: Read'\n"
              "(plus Metadata/Contents: Read) on the repos, and you must have push access.")
        return 1


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("ERROR: GH_TOKEN is not set. Add it as a repository secret (Settings > Secrets and variables > Actions).")
    SESSION.headers.update({
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "github-traffic-analytics"})
    cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}

    try:
        me = request("/user")
    except ApiError as e:
        sys.exit(f"ERROR: token rejected ({e}). Use a personal access token, not the built-in GITHUB_TOKEN.")
    login = me.json()["login"]
    repos = discover(cfg, login)

    if "--check" in sys.argv:
        sys.exit(check(repos, login, me.headers.get("X-OAuth-Scopes")))

    store, d = Store(), today()
    traffic_ok, errors = 0, 0
    print(f"{d} UTC - collecting {len(repos)} repositories for {login}")
    for full in repos:
        try:
            ok, problems = collect_repo(store, full, d, cfg)
        except ApiError as e:
            ok, problems = False, [str(e)]
        traffic_ok += ok
        errors += len(problems)
        print(f"  {'ok ' if ok else 'ERR'} {full}")
        for p in problems:
            print(f"      - {p}")
    store.upsert("runs", {"run_at": now_iso(), "repos": len(repos), "traffic_ok": traffic_ok, "errors": errors})
    store.save()
    print(f"Done. traffic collected for {traffic_ok}/{len(repos)} repos, {errors} problem(s).")
    if repos and traffic_ok == 0:
        sys.exit("ERROR: traffic could not be read for any repo - run with --check (token permissions are the usual cause).")


if __name__ == "__main__":
    main()
