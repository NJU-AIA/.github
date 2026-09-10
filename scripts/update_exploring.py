#!/usr/bin/env python3
"""Refresh the organization profile's Start exploring section from nju-aia.com."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

API_URL = "https://nju-aia.com/api/articles"
SITE_URL = "https://nju-aia.com"
README = Path("profile/README.md")
START = "<!-- AIA_FEED:START -->"
END = "<!-- AIA_FEED:END -->"
MAX_ITEMS = 6

CATEGORY_LABELS = {
    "tutorial": "Tutorial",
    "activity": "Activity",
    "preview": "Preview",
}


def fetch_articles() -> list[dict]:
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "NJU-AIA-GitHub-Profile/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"API returned HTTP {response.status}")
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to fetch {API_URL}: {exc}") from exc

    items = payload.get("items")
    if not isinstance(items, list):
        raise RuntimeError("API response does not contain an items list")
    return items


def normalized_date(value: object) -> date:
    if not isinstance(value, str):
        return date.min
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return date.min


def select_articles(items: list[dict]) -> list[dict]:
    valid = []
    for item in items:
        if not isinstance(item, dict) or item.get("published") is not True:
            continue
        if not all(isinstance(item.get(key), str) and item[key].strip() for key in ("id", "title")):
            continue
        valid.append(item)

    valid.sort(
        key=lambda item: (
            normalized_date(item.get("date")),
            str(item.get("updatedAt", "")),
        ),
        reverse=True,
    )
    return valid[:MAX_ITEMS]


def escape_markdown(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def render(items: list[dict]) -> str:
    if not items:
        raise RuntimeError("API returned no published articles")

    lines = []
    for item in items:
        title = escape_markdown(item["title"].strip())
        article_id = item["id"].strip()
        category = CATEGORY_LABELS.get(str(item.get("category", "")).lower(), "Article")
        published = str(item.get("date", "")).strip()
        author = str(item.get("author", "")).strip()

        metadata = [category]
        if published:
            metadata.append(published)
        if author:
            metadata.append(author)
        meta = " · ".join(metadata)
        lines.append(f"- **[{title}]({SITE_URL}/reader?id={article_id})**  \n  <sub>{meta}</sub>")

    return "\n".join(lines)


def update_readme(block: str) -> bool:
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise RuntimeError(f"missing {START} / {END} markers in {README}")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    updated = f"{before}{START}\n{block}\n{END}{after}"
    if updated == text:
        return False
    README.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    try:
        articles = select_articles(fetch_articles())
        changed = update_readme(render(articles))
    except Exception as exc:  # keep workflow failures explicit and actionable
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"selected {len(articles)} article(s); README {'updated' if changed else 'already current'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
