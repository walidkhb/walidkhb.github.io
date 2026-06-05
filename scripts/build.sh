#!/usr/bin/env bash
# Regenerate all derived blog assets. Run after adding or editing an article.
#
#   ./scripts/build.sh
#
# Steps:
#   1. build_blog_data   -> feed.xml + assets/data/articles.json (RSS + search index)
#   2. generate_og_images-> assets/img/og/<slug>.png (social share cards)
#   3. inject_head_meta  -> og:image / RSS link / schema into the HTML (idempotent)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "› Building feed + search index…"
python3 scripts/build_blog_data.py
echo
echo "› Generating social images…"
python3 scripts/generate_og_images.py
echo
echo "› Injecting head metadata…"
python3 scripts/inject_head_meta.py
echo
echo "✓ Done. Review changes with: git status"
