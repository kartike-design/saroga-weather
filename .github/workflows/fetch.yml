import os
import json
import base64
import urllib.request
import urllib.error

TOKEN = os.environ["GH_TOKEN"]
REPO  = os.environ["GH_REPO"]
PATH  = "docs/weather.json"
BRANCH = "data"

with open(PATH, "rb") as f:
    content = base64.b64encode(f.read()).decode()

api_url = f"https://api.github.com/repos/{REPO}/contents/{PATH}"

# Get current SHA of the file on data branch (needed for update)
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

# Write file to data branch via API
payload = json.dumps({
    "message": "Update weather data",
    "content": content,
    "branch": BRANCH,
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
    print(f"Done — wrote {PATH} to branch {BRANCH}, commit {result['commit']['sha'][:7]}")
