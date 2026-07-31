import os
import json
import base64
import urllib.request
import urllib.error

TOKEN  = os.environ["GH_TOKEN"]
REPO   = os.environ["GH_REPO"]
BRANCH = "data"

def api_request(url, method="GET", payload=None):
    req = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e

def get_sha(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    result, err = api_request(url)
    return result["sha"] if result else None

def push_file(path, local_path):
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    sha = get_sha(path)
    payload = json.dumps({
        "message": f"Update {path}",
        "content": content,
        "branch":  BRANCH,
        **({"sha": sha} if sha else {})
    }).encode()
    result, err = api_request(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        method="PUT",
        payload=payload
    )
    if result:
        print(f"Pushed {path} → commit {result['commit']['sha'][:7]}")
    else:
        print(f"Failed to push {path}: {err}")

def delete_file(path, sha):
    payload = json.dumps({
        "message": f"Remove old data file {path}",
        "sha":     sha,
        "branch":  BRANCH
    }).encode()
    result, err = api_request(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        method="DELETE",
        payload=payload
    )
    if result:
        print(f"Deleted {path}")
    else:
        print(f"Failed to delete {path}: {err}")

def cleanup_old_data_files(keep_latest_ts):
    url = f"https://api.github.com/repos/{REPO}/contents/docs?ref={BRANCH}"
    result, err = api_request(url)
    if not result:
        print(f"Could not list docs: {err}")
        return
    for item in result:
        name = item["name"]
        if name.startswith("data_") and name.endswith(".json"):
            ts = name[5:-5]
            if ts != keep_latest_ts:
                print(f"Removing old file: {name}")
                delete_file(f"docs/{name}", item["sha"])

def main():
    push_file("docs/weather.json", "docs/weather.json")

    if os.path.exists("docs/latest.txt"):
        push_file("docs/latest.txt", "docs/latest.txt")

    with open("docs/latest.txt") as f:
        ts = f.read().strip()

    ts_path = f"docs/data_{ts}.json"
    if os.path.exists(ts_path):
        push_file(ts_path, ts_path)
    else:
        print(f"Warning: {ts_path} not found")

    cleanup_old_data_files(ts)

if __name__ == "__main__":
    main()
