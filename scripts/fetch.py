import os, requests, json, datetime

# Create main data folder if not exists
os.makedirs("data", exist_ok=True)

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise SystemExit("Environment variable TOKEN is required for GitHub API authentication.")

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
USERNAME = "jadhavS04"   # <-- replace with your GitHub username


def fetch(endpoint, repo):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/{endpoint}"
    r = requests.get(url, headers=HEADERS)
    if not r.ok:
        raise SystemExit(f"Failed to fetch {endpoint} for {repo}: {r.status_code} {r.text}")
    return r.json()


def fetch_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100"
    r = requests.get(url, headers=HEADERS)
    if not r.ok:
        raise SystemExit(f"Failed to fetch repo list for {USERNAME}: {r.status_code} {r.text}")
    # Exclude forks — traffic API only works on repos you own
    return [repo for repo in r.json() if not repo["fork"]]

repos = fetch_repos()

today = datetime.date.today().isoformat()

for repo_info in repos:
    repo = repo_info["name"]

    # Fetch traffic data
    views = fetch("traffic/views", repo)
    clones = fetch("traffic/clones", repo)
    refs = fetch("traffic/popular/referrers", repo)
    paths = fetch("traffic/popular/paths", repo)

    # Organize data folders
    folders = {
        "views": views,
        "clones": clones,
        "referrers": refs,
        "paths": paths,
    }

    for folder, data in folders.items():
        folder_path = f"data/{folder}"
        os.makedirs(folder_path, exist_ok=True)

        file_path = f"{folder_path}/{repo}-{today}.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

print("Traffic data saved.")
