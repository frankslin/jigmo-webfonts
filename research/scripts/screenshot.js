// Screenshot + measure the repro pages with Playwright, using the
// pre-installed Chromium at /opt/pw-browsers/chromium.
const { chromium } = require('playwright');
const path = require('path');

const BASE = process.argv[2] || 'http://127.0.0.1:8931';
const OUTDIR = process.argv[3] || path.join(__dirname, '..', 'repro', 'screenshots');

(async () => {
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium',
  });
  const page = await browser.newPage({ viewport: { width: 1400, height: 4000 } });

  const consoleLines = [];
  page.on('console', (msg) => consoleLines.push(msg.text()));

  console.log('Loading index.html ...');
  await page.goto(`${BASE}/index.html`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUTDIR, 'index-full.png'), fullPage: true });

  // per-variant screenshots
  for (const key of ['gf-cdn', 'gf-selfhost', 'adobe-full', 'adobe-keep', 'adobe-default']) {
    const el = await page.$(`#variant-${key}`);
    if (el) {
      await el.screenshot({ path: path.join(OUTDIR, `variant-${key}.png`) });
    }
  }

  const measureLine = consoleLines.find((l) => l.startsWith('MEASURE_RESULTS_JSON:'));
  let measureResults = null;
  if (measureLine) {
    measureResults = JSON.parse(measureLine.slice('MEASURE_RESULTS_JSON:'.length));
  }

  console.log('Loading measure.html ...');
  const consoleLines2 = [];
  page.on('console', (msg) => consoleLines2.push(msg.text()));
  await page.goto(`${BASE}/measure.html`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUTDIR, 'measure-full.png'), fullPage: true });

  const measure2Line = consoleLines2.find((l) => l.startsWith('MEASURE2_RESULTS_JSON:'));
  let measure2Results = null;
  if (measure2Line) {
    measure2Results = JSON.parse(measure2Line.slice('MEASURE2_RESULTS_JSON:'.length));
  }

  await browser.close();

  const fs = require('fs');
  fs.writeFileSync(
    path.join(__dirname, '..', 'data', 'measure-index.json'),
    JSON.stringify(measureResults, null, 2)
  );
  fs.writeFileSync(
    path.join(__dirname, '..', 'data', 'measure-experiment.json'),
    JSON.stringify(measure2Results, null, 2)
  );

  console.log('=== index.html measurements ===');
  console.log(JSON.stringify(measureResults, null, 2));
  console.log('=== measure.html (pyftsubset experiment) measurements ===');
  console.log(JSON.stringify(measure2Results, null, 2));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
