// Rebuild the downloadable CV from scripts/cv/cv.html.
//
//   node scripts/cv/build_cv.js
//
// Needs Playwright with Chromium. Writes assets/Waleed-Albadawi-CV.pdf (A4, 2 pages).
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..', '..');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.join(__dirname, 'cv.html'), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);

  // Fail loudly if any page's content no longer fits on its sheet.
  const overflow = await page.evaluate(() =>
    [...document.querySelectorAll('.page')].map((p, i) => {
      const limit = p.getBoundingClientRect().bottom - 14; // keep clear of the footer
      const last = [...p.querySelectorAll('.body1 > *, .main > *, .side > *')]
        .reduce((m, el) => Math.max(m, el.getBoundingClientRect().bottom), 0);
      return last > limit ? `page ${i + 1} overflows by ${Math.round(last - limit)}px` : null;
    }).filter(Boolean));
  if (overflow.length) { console.error(overflow.join('\n')); process.exitCode = 1; }

  const out = path.join(root, 'assets', 'Waleed-Albadawi-CV.pdf');
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true, tagged: true, outline: false });
  await browser.close();
  console.log('Wrote', path.relative(root, out));
})();
