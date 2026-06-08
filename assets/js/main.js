// ============================================================================
// Waleed Albadawi — Executive site interactions
// Minimal, premium: header state, mobile menu, scroll reveal, active nav.
// ============================================================================

(function () {
  'use strict';

  // Header scroll state
  const header = document.getElementById('header');
  if (header) {
    const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // Mobile menu toggle
  const menuToggle = document.getElementById('menuToggle');
  const nav = document.getElementById('nav');
  if (menuToggle && nav) {
    menuToggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', String(isOpen));
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });
    nav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        nav.classList.remove('open');
        menuToggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
      });
    });
  }

  // Scroll-triggered reveal animation
  if ('IntersectionObserver' in window) {
    const reveal = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          reveal.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.fade-in').forEach((el) => reveal.observe(el));
  } else {
    document.querySelectorAll('.fade-in').forEach((el) => el.classList.add('visible'));
  }

  // Active nav highlighting (handles base + nested paths)
  const path = (window.location.pathname.split('/').filter(Boolean).pop() || 'index.html').toLowerCase();
  document.querySelectorAll('.site-nav a').forEach((link) => {
    const href = (link.getAttribute('href') || '').split('/').pop().toLowerCase();
    if (href === path) link.classList.add('active');
  });

  // Current year in footer
  document.querySelectorAll('[data-year]').forEach((el) => {
    el.textContent = String(new Date().getFullYear());
  });

  // "Also published on Medium" — injected from medium-links.json
  const articleBody = document.querySelector('.article-body');
  if (articleBody) {
    const match = window.location.pathname.match(/\/blog\/([^\/]+)\.html$/);
    if (match) {
      const slug = match[1];
      fetch('/medium-links.json')
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          const url = data && data.articles && data.articles[slug];
          if (!url) return;
          const wrap = document.createElement('div');
          wrap.style.cssText = 'margin-top:2.5rem;padding-top:1.5rem;border-top:1px solid var(--line);text-align:center;';
          wrap.innerHTML =
            '<a href="' + url + '" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:0.5rem;font-family:var(--font-body);font-size:0.78rem;color:var(--ink-muted);text-decoration:none;letter-spacing:0.18em;text-transform:uppercase;font-weight:600;">' +
            'Also published on Medium →</a>';
          articleBody.insertAdjacentElement('afterend', wrap);
        })
        .catch(() => {});
    }
  }
})();
