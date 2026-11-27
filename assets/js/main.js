// Header scroll effect
const header = document.getElementById('header');
if (header) {
  window.addEventListener('scroll', () => {
    header.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });
}

// Mobile menu toggle
const menuToggle = document.getElementById('menuToggle');
const nav = document.getElementById('nav');
if (menuToggle && nav) {
  menuToggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    menuToggle.setAttribute('aria-expanded', isOpen);
    menuToggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('open')) {
      nav.classList.remove('open');
      menuToggle.setAttribute('aria-expanded', 'false');
      menuToggle.setAttribute('aria-label', 'Open menu');
      menuToggle.focus();
    }
  });

  nav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      nav.classList.remove('open');
      menuToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// Scroll-triggered fade-in animations. Content is visible by default; the
// hidden state only applies once this script runs (html.js), and anything
// already on screen is revealed immediately so nothing flickers.
document.querySelectorAll('.fade-in').forEach(el => {
  if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add('visible');
});
document.documentElement.classList.add('js');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

// Active navigation state is written into the page by scripts/sync_layout.py.

// Wide tables, code blocks and diagrams scroll horizontally on small screens;
// make those scroll regions reachable and scrollable from the keyboard.
function markScrollRegions() {
  document.querySelectorAll('main pre, main table, main .diagram, main .code-block, main [class*="table-wrap"]').forEach(el => {
    if (el.scrollWidth > el.clientWidth + 1) {
      if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '0');
    } else if (el.getAttribute('tabindex') === '0' && el.dataset.scrollRegion !== 'static') {
      el.removeAttribute('tabindex');
    }
  });
}
window.addEventListener('load', markScrollRegions);
window.addEventListener('resize', () => { clearTimeout(window.__srT); window.__srT = setTimeout(markScrollRegions, 200); });

// "Also published on Medium" — injected from medium-links.json so publishing a
// post to Medium (and recording its URL there) lights up the link automatically.
(function () {
  const body = document.querySelector('.article-body');
  if (!body) return;
  const match = window.location.pathname.match(/\/blog\/([^\/]+)\.html$/);
  if (!match) return;
  const slug = match[1];
  fetch('/medium-links.json')
    .then(r => (r.ok ? r.json() : null))
    .then(data => {
      const url = data && data.articles && data.articles[slug];
      if (!url) return;
      const wrap = document.createElement('div');
      wrap.style.cssText = 'margin-top:2.5rem;padding-top:1.5rem;border-top:1px solid var(--color-border);text-align:center;';
      wrap.innerHTML =
        '<a href="' + url + '" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:0.5rem;font-family:var(--font-mono);font-size:0.8125rem;color:var(--color-text-muted);text-decoration:none;letter-spacing:0.04em;">' +
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M13.54 12a6.8 6.8 0 01-6.77 6.82A6.8 6.8 0 010 12a6.8 6.8 0 016.77-6.82A6.8 6.8 0 0113.54 12zM20.96 12c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42M24 12c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75C23.47 6.25 24 8.83 24 12z"/></svg>' +
        'ALSO PUBLISHED ON MEDIUM →</a>';
      body.insertAdjacentElement('afterend', wrap);
    })
    .catch(() => {});
})();

// Service worker: cache site assets for fast repeat visits (pages stay network-first).
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
