
# GitHub Traffic Analytics

This repository automatically collects **lifetime GitHub traffic analytics**, bypassing the 14‑day limit of GitHub.

## Features
✔ Stores unlimited traffic history  
✔ Daily automated GitHub Action  
✔ Views, clones, referrers, top paths  
✔ Dashboard-ready data  
✔ HTML dashboard included  

## Setup Instructions

### 1. Add GitHub Token
Go to:
**Settings → Secrets → Actions → New Secret**

Name it:
```
GH_TOKEN
```

### 2. Replace your username
Edit:
`scripts/fetch.py`

Replace:
```
USERNAME = "YOUR_GITHUB_USERNAME"
```

### 3. Push Everything
GitHub Action will run daily and store traffic forever.

---

## Dashboard
Open:
```
dashboard/index.html
```

You can extend it using Plotly graphs.

---

## Folder Structure
```
data/
scripts/
dashboard/
.github/workflows/
```
