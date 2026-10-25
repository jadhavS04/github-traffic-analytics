# GitHub Traffic Analytics

GitHub only keeps the **last 14 days** of views and clones. This repo saves them every day and keeps them forever.

- Runs by itself on GitHub Actions (00:15 and 12:15 UTC)
- Same date collected again → **overwritten** with the newest number. New date → **appended**.
- Covers every repo you own automatically (public, non-fork by default)
- Saves views, clones, referrers, popular pages, stars, forks, watchers, issues, PRs, release downloads, languages and commits
- Dashboard with trends, comparisons, insights and CSV export

## Setup (about 5 minutes)

### 0. Delete the old version
Remove `.github/workflows/traffic.yml`, `scripts/fetch.py` and `dashboard/` from the repo, or the old workflow keeps running and failing every day.

### 1. Create a token
GitHub's built-in Actions token **cannot read traffic**, so you need your own.

- Classic token: https://github.com/settings/tokens → *Generate new token (classic)* → tick **`repo`**
- Or fine-grained: all repositories, permissions **Administration: Read**, **Contents: Read**, **Metadata: Read**

### 2. Save it as a secret
This repo → **Settings → Secrets and variables → Actions → New repository secret**
Name: `GH_TOKEN` · Value: the token
(A secret you already named `GH_PAT` also works.)

### 3. Allow the workflow to save data
**Settings → Actions → General → Workflow permissions → Read and write permissions → Save**

### 4. Run it once
**Actions** tab → *Collect GitHub traffic* → **Run workflow**. Open the run and check the log: each repo should show `ok`.

### 5. Turn on the dashboard
**Settings → Pages → Deploy from a branch → `main` / `/docs` → Save.**
Your dashboard will be at `https://<your-username>.github.io/github-traffic-analytics/`.

## Settings (`config.json`)

| Key | Meaning |
|---|---|
| `owner` | Leave empty to use the token owner |
| `repos` | Only track these (e.g. `["geopower-index"]`). Empty = everything you own |
| `exclude` | Repo names to skip |
| `include_forks`, `include_archived`, `include_private` | Default `false` |

> **Private repos:** the data lands in this repo's CSV files. If this repo is public, anyone can read it, so `include_private` is off by default.

## If it is not working

Run the check on your computer:

```bash
pip install -r requirements.txt
GH_TOKEN=your_token python scripts/collect.py --check
```

| Symptom in the Actions log | Cause |
|---|---|
| `GH_TOKEN is not set` | Secret missing or misspelt (must be exactly `GH_TOKEN`) |
| `token rejected` | Expired token, or the built-in `GITHUB_TOKEN` was used |
| `HTTP 403 ... traffic/views` | Token lacks `repo` (classic) or *Administration: Read* (fine-grained) |
| `HTTP 404 ... traffic` | Token owner has no push access to that repo |
| Run is green but nothing is committed | Step 3 (read and write permissions) not done |
| Dashboard says "No traffic saved yet" | Run the workflow once; Pages must point to `/docs` |
| Workflow stopped after weeks | GitHub pauses schedules on inactive repos; open Actions and re-enable it |

## What you can and cannot get

- History starts the day you first run it. GitHub cannot give you older traffic.
- Run it at least every 14 days or you lose the gap. Daily is safe.
- Referrers and popular pages are GitHub's **top 10 over a rolling 14 days**, so they are saved as one snapshot per day, not true daily numbers.
- "Unique visitors" are unique per day. Adding days together counts a returning person again.
- Today's numbers are partial until the 00:15 UTC run finalises them.

## Files

```
.github/workflows/collect.yml   schedule + commit
scripts/collect.py              fetches from the GitHub API, merges into data/
scripts/build_dashboard.py      data/*.csv → docs/data.js
docs/index.html                 the dashboard
data/*.csv                      your permanent history
config.json                     what to track
```
