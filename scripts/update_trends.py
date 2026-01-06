import json
import time
import urllib.request

REDDIT_URL = "https://old.reddit.com/r/all/rising.json?limit=50"
USER_AGENT = "trend-radar-bot/1.0 (by u/poopshoes420)"

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    payload = fetch_json(REDDIT_URL)
    children = payload.get("data", {}).get("children", [])

    items = []
    now = time.time()

    for c in children:
        d = c.get("data", {})
        title = d.get("title") or ""
        if not title:
            continue

        upvotes = int(d.get("ups") or 0)
        comments = int(d.get("num_comments") or 0)
        created = float(d.get("created_utc") or now)
        age_minutes = max(1.0, (now - created) / 60.0)

        # simple "velocity-ish" score: interaction per minute + a small boost for being very fresh
        velocity = (upvotes + (2 * comments)) / age_minutes

        items.append({
            "topic": title,
            "sources": ["reddit"],
            "why": f"Rising on r/all • {upvotes} upvotes • {comments} comments • ~{int(age_minutes)}m old",
            "_score": velocity
        })

    # Sort and keep top 20
    items.sort(key=lambda x: x["_score"], reverse=True)
    top = [{k: v for k, v in item.items() if k != "_score"} for item in items[:20]]

    with open("data/trends.json", "w") as f:
        json.dump(top, f, indent=2)

if __name__ == "__main__":
    main()
