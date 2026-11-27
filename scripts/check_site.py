#!/usr/bin/env python3
"""Static quality checks for the site. Exit code 1 if anything fails.

    python3 scripts/check_site.py

Checks every page for: HTML that parses, exactly one <h1>, no skipped heading
levels, valid JSON-LD, images with alt text, internal links and in-page anchors
that resolve, and wording that the claims register does not allow on the site.
"""
import glob, html, json, os, re, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SKIP = {'train-speed.html'}
PAGES = sorted(p for p in glob.glob('**/*.html', recursive=True)
               if not p.startswith(('scripts/', 'partials/', 'google')) and p not in SKIP)

# Wording the claims register does not allow (unverified, contradictory, sensitive or private).
BANNED = {
    r'8\s?% (?:increase|of annual|to annual|profit)|annual profit[^.]{0,40}8\s?%': 'unverified 8% profit claim',
    r'70\s?% faster|faster[^.]{0,30}70\s?%': 'unverified 70% time-to-market claim',
    r'35\s?% (?:fraud|reduction)|fraud[^.]{0,30}35\s?%': 'unverified 35% fraud claim',
    r'50\+ systems|50\+</div>\s*<div[^>]*>Systems': 'unverified 50+ systems claim',
    r'every migration': 'overstated zero-downtime claim',
    r'Years Leading': 'misleading years-leading label',
    r'\bGPA\b': 'GPA should not be published',
    r'17 direct reports': 'unconfirmed reporting line',
    r'\+966|\+1 563': 'personal phone number on a web page',
    r'\b934\b|28 Accounting Events|Treasury Interfaces|Services Assessed': 'internal estate counts',
    r'\bMurex\b|\bTarabut\b|\bDXC\b|\bEquation core\b': 'internal vendor or system name',
    r'[Zz]ero-[Tt]ouch [Ii]ntegration|fully automated to production': 'overstated automation claim',
    r'CTO, CIO|Open to executive': 'explicit role targeting',
}

errors = []
ids, texts = {}, {}
for p in PAGES:
    s = open(p, encoding='utf-8').read()
    try:
        HTMLParser().feed(s)
    except Exception as e:
        errors.append(f'{p}: HTML parse error {e}')
    ids[os.path.normpath(p)] = set(re.findall(r'\bid="([^"]+)"', s))
    body = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    texts[p] = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    if p != '404.html':
        n = len(re.findall(r'<h1[\s>]', body))
        if n != 1:
            errors.append(f'{p}: {n} <h1> elements')
    levels = [int(x) for x in re.findall(r'<h([1-6])[\s>]', body)]
    for a, b in zip(levels, levels[1:]):
        if b > a + 1:
            errors.append(f'{p}: heading jumps h{a} -> h{b}')
            break
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            json.loads(m.group(1))
        except Exception as e:
            errors.append(f'{p}: invalid JSON-LD ({e})')
    for img in re.findall(r'<img\b[^>]*>', s):
        if 'alt=' not in img:
            errors.append(f'{p}: <img> without alt')
    for pat, why in BANNED.items():
        if re.search(pat, s):
            errors.append(f'{p}: {why}')

for p in PAGES:
    s = open(p, encoding='utf-8').read()
    for h in re.findall(r'href="([^"]+)"', s):
        if re.match(r'^(https?:|mailto:|tel:|javascript:|data:)', h) or h == '#' or "'" in h:
            continue
        u = urlsplit(h)
        if u.path:
            tgt = os.path.normpath(u.path.lstrip('/')) if u.path.startswith('/') else os.path.normpath(os.path.join(os.path.dirname(p), u.path))
            if os.path.isdir(tgt):
                tgt = os.path.join(tgt, 'index.html')
            if not os.path.exists(tgt):
                errors.append(f'{p}: broken link {h}')
                continue
        else:
            tgt = os.path.normpath(p)
        if u.fragment and tgt.endswith('.html') and u.fragment not in ids.get(os.path.normpath(tgt), set()):
            errors.append(f'{p}: missing anchor {h}')

print(f'{len(PAGES)} pages checked, {len(errors)} problem(s)')
for e in errors:
    print('  ' + e)
sys.exit(1 if errors else 0)
