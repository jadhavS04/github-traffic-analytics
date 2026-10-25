"""Table definitions shared by the collector and the dashboard builder.

key  = columns that identify a row (writing the same key again OVERWRITES it)
cols = all CSV columns, in order
num  = columns stored as numbers
"""

TABLES = {
    # --- daily history (this is what GitHub only keeps for 14 days) -------
    "views": {"key": ["repo", "date"], "cols": ["repo", "date", "views", "uniques"], "num": ["views", "uniques"]},
    "clones": {"key": ["repo", "date"], "cols": ["repo", "date", "clones", "uniques"], "num": ["clones", "uniques"]},
    # --- rolling 14-day snapshots, one per collection day ------------------
    "referrers": {"key": ["repo", "date", "referrer"], "cols": ["repo", "date", "referrer", "count", "uniques"], "num": ["count", "uniques"]},
    "paths": {"key": ["repo", "date", "path"], "cols": ["repo", "date", "path", "title", "count", "uniques"], "num": ["count", "uniques"]},
    # --- repo health, one snapshot per day ---------------------------------
    "repo_stats": {"key": ["repo", "date"], "cols": ["repo", "date", "stars", "forks", "watchers", "open_issues", "open_prs", "size_kb"], "num": ["stars", "forks", "watchers", "open_issues", "open_prs", "size_kb"]},
    "releases": {"key": ["repo", "date", "tag", "asset"], "cols": ["repo", "date", "tag", "asset", "downloads"], "num": ["downloads"]},
    "languages": {"key": ["repo", "date", "language"], "cols": ["repo", "date", "language", "bytes"], "num": ["bytes"]},
    "commits": {"key": ["repo", "date"], "cols": ["repo", "date", "commits"], "num": ["commits"]},
    # --- who/when (full history, replaced per repo on refresh) -------------
    "stargazers": {"key": ["repo", "user"], "cols": ["repo", "user", "starred_at"], "num": []},
    "forks": {"key": ["repo", "fork"], "cols": ["repo", "fork", "created_at"], "num": []},
    # --- bookkeeping ------------------------------------------------------
    "runs": {"key": ["run_at"], "cols": ["run_at", "repos", "traffic_ok", "errors"], "num": ["repos", "traffic_ok", "errors"]},
}
