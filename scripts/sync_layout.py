#!/usr/bin/env python3
"""Stamp the shared header and footer (partials/) into every page.

    python3 scripts/sync_layout.py

Idempotent. Also guarantees a skip link and a <main id="main"> landmark.
Pages without a site header (404, standalone tools) are left alone.
"""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
HEADER = open('partials/header.html').read().rstrip('\n')
FOOTER = open('partials/footer.html').read().rstrip('\n')
SKIP = {'train-speed.html', '404.html'}


def section(path):
    if path.startswith('lab/') or path == 'technical.html':
        return 'lab'
    if path.startswith('blog/') or path == 'blog.html':
        return 'blog'
    return os.path.splitext(os.path.basename(path))[0]


def render(tpl, path):
    root = '../' * path.count('/')
    cur = section(path)
    out = tpl.replace('{{root}}', root)
    for key in ('about', 'experience', 'projects', 'blog', 'lab', 'resume'):
        out = out.replace('{{active:%s}}' % key, ' class="active" aria-current="page"' if cur == key else '')
    out = out.replace('{{activecls:contact}}', ' active' if cur == 'contact' else '')
    out = out.replace('{{aria:contact}}', ' aria-current="page"' if cur == 'contact' else '')
    return out


changed = 0
for path in sorted(glob.glob('**/*.html', recursive=True)):
    if path.startswith(('scripts/', 'partials/')) or path in SKIP or path.startswith('google'):
        continue
    s = open(path).read()
    if '<header class="site-header"' not in s:
        continue
    orig = s
    s = re.sub(r'(?:<a class="skip-link"[^>]*>[^<]*</a>\s*)?<header class="site-header".*?</header>',
               lambda m: render(HEADER, path), s, count=1, flags=re.S)
    s = re.sub(r'<footer class="site-footer[^"]*".*?</footer>', lambda m: render(FOOTER, path), s, count=1, flags=re.S)
    if '<main id="main"' not in s:
        s = s.replace('</header>', '</header>\n\n  <main id="main">', 1)
        i = s.rfind('<footer class="site-footer"')
        s = s[:i] + '</main>\n\n  ' + s[i:]
    if s != orig:
        open(path, 'w').write(s)
        changed += 1
print('pages updated:', changed)
