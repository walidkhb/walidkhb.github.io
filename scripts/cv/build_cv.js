// Rebuild the downloadable CV from scripts/cv/cv.html.
//
//   node scripts/cv/build_cv.js
//
// Needs Playwright with Chromium. Writes assets/Waleed-Albadawi-CV.pdf (designed, A4, 2 pages)
// and assets/Waleed-Albadawi-CV-ATS.pdf (plain single column for applicant tracking systems).
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..', '..');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.join(__dirname, 'cv.html'), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);

  // Fail loudly if the CV is not exactly two sheets, or any sheet's content runs into its footer.
  const overflow = await page.evaluate(() => {
    const pages = [...document.querySelectorAll('.page')];
    const problems = pages.length === 2 ? [] : [`expected 2 pages, found ${pages.length}`];
    const spare = [];
    pages.forEach((p, i) => {
      const foot = p.querySelector('.foot');
      const limit = (foot ? foot.getBoundingClientRect().top : p.getBoundingClientRect().bottom) - 6;
      const last = [...p.querySelectorAll('.body1 > *, .main > *, .side > *')]
        .reduce((m, el) => Math.max(m, el.getBoundingClientRect().bottom), 0);
      if (last > limit) problems.push(`page ${i + 1} overflows by ${Math.round(last - limit)}px`);
      else spare.push(`page ${i + 1}: ${Math.round(limit - last)}px to spare`);
    });
    return { problems, spare };
  });
  console.log(overflow.spare.join(', '));
  if (overflow.problems.length) { console.error(overflow.problems.join('\n')); process.exitCode = 1; }

  const out = path.join(root, 'assets', 'Waleed-Albadawi-CV.pdf');
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true, tagged: true, outline: false });
  console.log('Wrote', path.relative(root, out));

  // Plain single-column version for applicant tracking systems.
  const ats = await browser.newPage();
  await ats.goto('file://' + path.join(__dirname, 'cv-ats.html'), { waitUntil: 'load' });
  const atsOut = path.join(root, 'assets', 'Waleed-Albadawi-CV-ATS.pdf');
  await ats.pdf({ path: atsOut, format: 'A4', preferCSSPageSize: true, tagged: true });
  console.log('Wrote', path.relative(root, atsOut));
  await browser.close();
})();
