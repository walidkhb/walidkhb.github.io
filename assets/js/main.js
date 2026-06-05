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
  });

  nav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      nav.classList.remove('open');
      menuToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// Scroll-triggered fade-in animations
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

// Active navigation highlighting
const currentPage = window.location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('.site-nav a').forEach(link => {
  const href = link.getAttribute('href');
  if (href === currentPage) {
    link.classList.add('active');
  }
});

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
