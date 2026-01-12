
import os, requests, json, datetime

TOKEN = os.environ["TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
USERNAME = "jadhavS04"   # <-- replace

def fetch(endpoint, repo):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/{endpoint}"
    r = requests.get(url, headers=HEADERS)
    return r.json()

repos = requests.get(f"https://api.github.com/users/{USERNAME}/repos", headers=HEADERS).json()
today = datetime.date.today().isoformat()

for repo_info in repos:
    repo = repo_info["name"]

    views = fetch("traffic/views", repo)
    clones = fetch("traffic/clones", repo)
    refs = fetch("traffic/popular/referrers", repo)
    paths = fetch("traffic/popular/paths", repo)

    folders = {
        "views": views,
        "clones": clones,
        "referrers": refs,
        "paths": paths,
    }

    for folder, data in folders.items():
        path = f"data/{folder}/{repo}-{today}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

print("Traffic data saved.")
