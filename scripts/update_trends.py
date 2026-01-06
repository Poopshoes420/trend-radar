import json
import time
import urllib.request
import xml.etree.ElementTree as ET

import os
import urllib.parse


# RSS feeds are much less likely to get blocked than Reddit JSON endpoints.
FEEDS = [
    "https://www.reddit.com/r/all/.rss?sort=new",

    "https://www.reddit.com/r/socialmedia/.rss?sort=new",
    "https://www.reddit.com/r/worldnews/.rss?sort=new",
    "https://www.reddit.com/r/funny/.rss?sort=new",
    "https://www.reddit.com/r/gaming/.rss?sort=new",
    "https://www.reddit.com/r/youtube/.rss?sort=new",
]


SUBREDDIT_WEIGHTS = {
    "all": 1.0,
    "funny": 1.6,
    "youtube": 1.4,
    "worldnews": 1.3,
    "gaming": 1.2,
    "popculturechat": 1.2,
}

USER_AGENT = "trend-radar-bot/1.0 (github-actions)"

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_TRENDING_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
    "?part=snippet,statistics"
    "&chart=mostPopular"
    "&regionCode=US"
    "&maxResults=25"
)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_rss(xml_text: str):
    root = ET.fromstring(xml_text)
    # RSS is Atom format here
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall("a:entry", ns)
    out = []
    now = time.time()

    for e in entries:
        title_el = e.find("a:title", ns)
        link_el = e.find("a:link", ns)
        updated_el = e.find("a:updated", ns)

        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue

        link = link_el.attrib.get("href") if link_el is not None else ""
        updated = (updated_el.text or "").strip() if updated_el is not None else ""

        age_minutes = 1
        try:
            t = time.strptime(updated[:19], "%Y-%m-%dT%H:%M:%S")
            updated_ts = time.mktime(t)
            age_minutes = max(1, int((now - updated_ts) / 60))
        except Exception:
            pass

        # extract subreddit from the link
        subreddit = "unknown"
        if link:
            parts = link.split("/r/")
            if len(parts) > 1:
                subreddit = parts[1].split("/")[0]

        # velocity score
        weight = SUBREDDIT_WEIGHTS.get(subreddit, 1.0)
        score = weight * (1.0 / age_minutes)

        out.append({
            "topic": title,
            "sources": ["reddit"],
            "subreddit": subreddit,
            "why": f"New post on r/{subreddit} • ~{age_minutes}m ago",
            "exampleUrl": link,
            "_score": score
        })


 
    return out

def fetch_youtube_trending():
    if not YOUTUBE_API_KEY:
        return []

    url = f"{YOUTUBE_TRENDING_URL}&key={urllib.parse.quote(YOUTUBE_API_KEY)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    items = []
    now = time.time()

    for v in data.get("items", []):
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})

        title = snippet.get("title")
        published = snippet.get("publishedAt", "")
        views = int(stats.get("viewCount", 0))

        if not title or not published:
            continue

        try:
            t = time.strptime(published[:19], "%Y-%m-%dT%H:%M:%S")
            published_ts = time.mktime(t)
            age_minutes = max(1, int((now - published_ts) / 60))
        except Exception:
            age_minutes = 1

        # Velocity = views per minute
        score = views / age_minutes

        items.append({
            "topic": title,
            "sources": ["youtube"],
            "why": f"Trending on YouTube • {views:,} views • ~{age_minutes}m old",
            "exampleUrl": f"https://www.youtube.com/watch?v={v.get('id')}",
            "_score": score
        })

    return items


def main():
    all_items = []
    seen_titles = set()

    for url in FEEDS:
        xml_text = fetch_text(url)
        items = parse_rss(xml_text)
        for it in items:
            key = it["topic"].lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            all_items.append(it)

        all_items.extend(fetch_youtube_trending())

    # Rank by velocity score (higher first)
    all_items.sort(key=lambda x: x.get("_score", 0), reverse=True)

    # Keep top 20 and remove internal score
    top = []
    for item in all_items[:20]:
        item = {k: v for k, v in item.items() if k != "_score"}
        top.append(item)

    with open("data/trends.json", "w") as f:
        json.dump(top, f, indent=2)

if __name__ == "__main__":
    main()
