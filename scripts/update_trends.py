import json

data = [
  {
    "topic": "Reddit debate over new AI video tools",
    "sources": ["reddit"],
    "why": "Multiple fast-rising threads today"
  },
  {
    "topic": "YouTube Shorts format gaining traction",
    "sources": ["youtube"],
    "why": "Several creators posting similar formats"
  }
]

with open("data/trends.json", "w") as f:
    json.dump(data, f, indent=2)

