import json
import time
import urllib.request
import xml.etree.ElementTree as ET

# RSS feeds are much less likely to get blocked than Reddit JSON endpoints.
FEEDS = [
    # Broad catch-all
    "https://www.reddit.com/r/all/.rss?sort=new",

    # Specifics (edit this list anytime)
    "https://www.reddit.com/r/socialmedia/.rss?sort=new",
    "https://www.reddit.com/r/worldnews/.rss?sort=new",
    "https://www.reddit.com/r/funny/.rss?sort=new",
    "https://www.reddit.com/r/gaming/.rss?sort=new",
    "https://www.reddit.com/r/youtube/.rss?sort=new",
]

USER_AGENT = "trend-radar-bot/1.0 (github-actions)"

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

        # We don’t get upvotes/comments via RSS, so we rank by recency.
        # If updated parses badly, treat as "now".
        age_minutes = 1
        try:
            # format like 2026-01-06T15:03:21+00:00
            # simple parse: take first 19 chars "YYYY-MM-DDTHH:MM:SS"
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

        out.append({
            "topic": title,
            "sources": ["reddit"],
            "subreddit": subreddit,
            "why": f"New post on r/{subreddit} • ~{age_minutes}m ago",
            "exampleUrl": link
        })
 
    return out

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

    # Keep top 20 (they’re already basically newest-first)
    top = all_items[:20]

    with open("data/trends.json", "w") as f:
        json.dump(top, f, indent=2)

if __name__ == "__main__":
    main()
