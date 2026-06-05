#!/usr/bin/env python3
"""
Idempotently inject head metadata into the site's HTML:

  - Per-article social image     og:image / twitter:image  ->  /assets/img/og/<slug>.png
  - RSS discovery link           <link rel="alternate" ... href="/feed.xml">  (all blog pages + home)
  - BlogPosting "image" schema   so search engines pick up the article image
  - Category ItemList schema     enriches each CollectionPage with its list of articles

Safe to run repeatedly: every insertion is guarded by a marker check.
"""

import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.wbadawi.info"
RSS_LINK = (
    '<link rel="alternate" type="application/rss+xml" '
    'title="Waleed Albadawi — Insights" href="/feed.xml">'
)
JSONLD_RE = re.compile(
    r'(<script type="application/ld\+json">\s*)(\{.*?\})(\s*</script>)', re.S
)
CANON_RE = re.compile(r'([ \t]*)(<link rel="canonical"[^>]*>)')


def og_url(slug):
    return f"{SITE}/assets/img/og/{slug}.png"


def insert_after_canonical(text, block):
    """Insert an indented block immediately after the canonical link."""
    m = CANON_RE.search(text)
    if not m:
        return text
    indent = m.group(1)
    add = "\n" + "\n".join(indent + line for line in block)
    return text[: m.end()] + add + text[m.end():]


def edit_jsonld(text, mutate):
    """Run mutate(obj) -> obj|None over each JSON-LD block, re-serialising changes."""
    def repl(m):
        try:
            obj = json.loads(m.group(2))
        except json.JSONDecodeError:
            return m.group(0)
        new = mutate(obj)
        if new is None:
            return m.group(0)
        dumped = json.dumps(new, ensure_ascii=False, indent=2)
        dumped = "\n".join("  " + ln for ln in dumped.splitlines())
        return m.group(1) + dumped.strip() + m.group(3)

    return JSONLD_RE.sub(repl, text)


def category_items(text):
    """Pull (url, title) pairs from a category page's article list."""
    items = []
    for href, block in re.findall(
        r'<a href="([^"]+\.html)" class="article-list__link">(.*?)</a>', text, re.S
    ):
        tm = re.search(r'article-list__title">(.*?)</div>', block, re.S)
        if tm:
            items.append((href, html.unescape(tm.group(1).strip())))
    return items


def process(path):
    text = original = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, ROOT)
    is_article = '"@type": "BlogPosting"' in text or '"@type":"BlogPosting"' in text
    is_category = "CollectionPage" in text
    slug = os.path.basename(path)[:-5]
    changes = []

    # 1. RSS discovery link (every page we touch)
    if "application/rss+xml" not in text:
        text = insert_after_canonical(text, [RSS_LINK])
        changes.append("rss-link")

    # 2. Per-article social image + BlogPosting image schema
    if is_article and "og:image" not in text:
        headline = ""
        hm = re.search(r'"headline":\s*"(.*?)"', text)
        if hm:
            headline = hm.group(1)
        block = [
            f'<meta property="og:image" content="{og_url(slug)}">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{html.escape(headline)} — Waleed Albadawi">',
            f'<meta name="twitter:image" content="{og_url(slug)}">',
        ]
        text = insert_after_canonical(text, block)
        changes.append("og:image")

        def add_image(obj):
            if obj.get("@type") == "BlogPosting" and "image" not in obj:
                # keep "image" right after headline for readability
                rebuilt = {}
                for k, v in obj.items():
                    rebuilt[k] = v
                    if k == "headline":
                        rebuilt["image"] = og_url(slug)
                return rebuilt
            return None

        text = edit_jsonld(text, add_image)
        changes.append("schema:image")

    # 3. Category pages: social image (reuse site card) + ItemList enrichment
    if is_category:
        if "og:image" not in text:
            block = [
                f'<meta property="og:image" content="{SITE}/assets/img/og-image.png">',
                f'<meta name="twitter:image" content="{SITE}/assets/img/og-image.png">',
            ]
            text = insert_after_canonical(text, block)
            text = text.replace(
                '<meta name="twitter:card" content="summary">',
                '<meta name="twitter:card" content="summary_large_image">',
            )
            changes.append("og:image")

        items = category_items(text)
        if items and '"mainEntity"' not in text:

            def add_list(obj):
                if obj.get("@type") == "CollectionPage" and "mainEntity" not in obj:
                    obj["mainEntity"] = {
                        "@type": "ItemList",
                        "itemListElement": [
                            {
                                "@type": "ListItem",
                                "position": i + 1,
                                "url": f"{SITE}/blog/{href}",
                                "name": title,
                            }
                            for i, (href, title) in enumerate(items)
                        ],
                    }
                    return obj
                return None

            text = edit_jsonld(text, add_list)
            changes.append(f"schema:itemlist({len(items)})")

    if text != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  {rel:<48} {', '.join(changes)}")
    return text != original


def main():
    targets = sorted(glob.glob(os.path.join(ROOT, "blog", "*.html")))
    targets += [os.path.join(ROOT, "index.html"), os.path.join(ROOT, "blog.html")]
    changed = sum(process(p) for p in targets)
    print(f"\n  {changed} file(s) updated.")


if __name__ == "__main__":
    main()
