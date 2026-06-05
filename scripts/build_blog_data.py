#!/usr/bin/env python3
"""
Build derived blog data from the article HTML files.

Scans blog/*.html, selects the individual articles (those carrying a
BlogPosting JSON-LD block), and emits two artifacts:

  - feed.xml                     RSS 2.0 feed (for readers / Medium import / newsletters)
  - assets/data/articles.json    Flat article index (powers blog search)

Re-run this whenever you add or edit an article. No third-party dependencies.
"""

import glob
import html
import json
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.wbadawi.info"
RIYADH = timezone(timedelta(hours=3))  # AST, no DST

JSONLD_RE = re.compile(
    r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', re.S
)


def first_jsonld(htmltext, wanted_type):
    """Return the first JSON-LD object whose @type matches wanted_type."""
    for blob in JSONLD_RE.findall(htmltext):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == wanted_type:
            return data
    return None


def meta(htmltext, name=None, prop=None):
    if name:
        m = re.search(
            r'<meta\s+name="%s"\s+content="(.*?)">' % re.escape(name), htmltext, re.S
        )
    else:
        m = re.search(
            r'<meta\s+property="%s"\s+content="(.*?)">' % re.escape(prop), htmltext, re.S
        )
    return html.unescape(m.group(1).strip()) if m else ""


def collect_articles():
    articles = []
    for path in sorted(glob.glob(os.path.join(ROOT, "blog", "*.html"))):
        text = open(path, encoding="utf-8").read()
        post = first_jsonld(text, "BlogPosting")
        if not post:
            continue  # category / hub pages are not articles
        slug = os.path.basename(path)[:-5]

        title = post.get("headline") or ""
        if not title:
            t = re.search(r"<title>(.*?)</title>", text, re.S)
            title = html.unescape(t.group(1).split("—")[0].strip()) if t else slug
        title = html.unescape(title).strip()

        desc = meta(text, name="description") or post.get("description", "")
        date = post.get("datePublished", "")
        url = post.get("url") or f"{SITE}/blog/{slug}.html"

        # Category comes from breadcrumb position 3 (Home > Insights > Category > Article)
        category = ""
        bc = post.get("breadcrumb", {})
        for item in bc.get("itemListElement", []):
            if item.get("position") == 3:
                category = html.unescape(item.get("name", ""))
                break

        articles.append(
            {
                "slug": slug,
                "title": title,
                "description": desc,
                "category": category,
                "date": date,
                "url": url,
                "relurl": f"blog/{slug}.html",
            }
        )

    # Newest first; stable by slug for equal dates
    articles.sort(key=lambda a: (a["date"], a["slug"]), reverse=True)
    return articles


def to_rfc822(date_str):
    try:
        y, m, d = (int(x) for x in date_str.split("-"))
        return format_datetime(datetime(y, m, d, 9, 0, 0, tzinfo=RIYADH))
    except Exception:
        return format_datetime(datetime.now(RIYADH))


def build_feed(articles):
    now = format_datetime(datetime(2026, 1, 1, 9, 0, 0, tzinfo=RIYADH))
    if articles:
        now = to_rfc822(articles[0]["date"])

    items = []
    for a in articles:
        items.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <title>{html.escape(a['title'])}</title>",
                    f"      <link>{html.escape(a['url'])}</link>",
                    f"      <guid isPermaLink=\"true\">{html.escape(a['url'])}</guid>",
                    f"      <pubDate>{to_rfc822(a['date'])}</pubDate>",
                    f"      <dc:creator>Waleed Albadawi</dc:creator>",
                    (f"      <category>{html.escape(a['category'])}</category>" if a["category"] else ""),
                    f"      <description><![CDATA[{a['description']}]]></description>",
                    "    </item>",
                ]
            ).replace("\n\n", "\n")
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Waleed Albadawi — Insights</title>
    <link>{SITE}/blog.html</link>
    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>Executive perspectives on enterprise integration, platform strategy, open banking KSA, payment modernisation, and technology leadership in Saudi Arabian financial services.</description>
    <language>en</language>
    <copyright>© Waleed Albadawi</copyright>
    <managingEditor>noreply@wbadawi.info (Waleed Albadawi)</managingEditor>
    <lastBuildDate>{now}</lastBuildDate>
    <image>
      <url>{SITE}/assets/img/favicon-192.png</url>
      <title>Waleed Albadawi — Insights</title>
      <link>{SITE}/blog.html</link>
    </image>
{chr(10).join(items)}
  </channel>
</rss>
"""


def main():
    articles = collect_articles()

    feed_path = os.path.join(ROOT, "feed.xml")
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(build_feed(articles))

    data_path = os.path.join(ROOT, "assets", "data", "articles.json")
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    index = [
        {
            "title": a["title"],
            "description": a["description"],
            "category": a["category"],
            "date": a["date"],
            "url": a["relurl"],
        }
        for a in articles
    ]
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"  feed.xml            {len(articles)} items")
    print(f"  articles.json       {len(index)} entries")
    for a in articles:
        print(f"    {a['date']}  {a['category']:<24}  {a['slug']}")


if __name__ == "__main__":
    main()
