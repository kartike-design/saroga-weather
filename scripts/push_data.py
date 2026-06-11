import os
import json
import base64
import urllib.request
import urllib.error

TOKEN  = os.environ["GH_TOKEN"]
REPO   = os.environ["GH_REPO"]
BRANCH = "data"

def push_file(path, local_path):
    api_url = f"https://api.github.com/repos/{REPO}/contents/{path}"

    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    # Get current SHA if file exists
    req = urllib.request.Request(
        f"{api_url}?ref={BRANCH}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json"
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            sha = json.loads(r.read())["sha"]
    except urllib.error.HTTPError:
        sha = None

    payload = json.dumps({
        "message": f"Update {path}",
        "content": content,
        "branch":  BRANCH,
        **({"sha": sha} if sha else {})
    }).encode()

    write_req = urllib.request.Request(
        api_url,
        data=payload,
        method="PUT",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(write_req) as r:
        result = json.loads(r.read())
        print(f"Pushed {path} → commit {result['commit']['sha'][:7]}")

def main():
    # Always push weather.json
    push_file("docs/weather.json", "docs/weather.json")

    # Push latest.txt
    if os.path.exists("docs/latest.txt"):
        push_file("docs/latest.txt", "docs/latest.txt")

    # Push the timestamped data file
    with open("docs/latest.txt") as f:
        ts = f.read().strip()
    ts_path = f"docs/data_{ts}.json"
    if os.path.exists(ts_path):
        push_file(ts_path, ts_path)
    else:
        print(f"Warning: {ts_path} not found")

if __name__ == "__main__":
    main()
