import { chromium } from 'playwright-core';
import Chromium, { inflate } from '@sparticuz/chromium';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { server } from '../server.js';
const require = createRequire(import.meta.url);
const libraryDirectory = await inflate(resolve(dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br'));
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
import AxeBuilder from '@axe-core/playwright';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
await mkdir('test-results', { recursive: true });
let browser;
try {
  browser = await chromium.launch({ executablePath: await Chromium.executablePath(), args: Chromium.args.filter(arg => !['--disable-web-security', '--allow-running-insecure-content'].includes(arg)), headless: true, env: { ...process.env, LD_LIBRARY_PATH: `${libraryDirectory}/lib:${process.env.LD_LIBRARY_PATH || ''}` } });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto(base);
  await page.screenshot({ path: 'test-results/desktop.png', fullPage: true });
  assert.equal(await page.locator('body').evaluate(el => el.scrollWidth <= innerWidth), true);
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  console.log('Accessibility violations:', JSON.stringify(axe.violations.map(x => ({ id: x.id, impact: x.impact, nodes: x.nodes.map(n => n.target) }))));
  assert.equal(axe.violations.length, 0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'test-results/mobile.png', fullPage: true });
  assert.equal(await page.locator('body').evaluate(el => el.scrollWidth <= innerWidth), true);
  await page.route('**/api/parse', route => route.fulfill({ json: {
    success: true, provider: 'diskwala', filename: 'Example video.mp4', sizeBytes: 512 * 1024 ** 2, canStream: true,
    streamUrl: '/api/media?mode=stream&token=test', downloadUrl: '/api/media?mode=download&token=test'
  } }));
  await page.locator('#linkInput').fill('https://diskwala.com/app/example');
  await page.locator('#processBtn').click();
  await page.locator('#result').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#player').getAttribute('src'), null);
  assert.equal(await page.locator('#streamBtn').isVisible(), true);
  await page.screenshot({ path: 'test-results/mobile-result.png', fullPage: true });
  await page.locator('#resetBtn').click();
  assert.equal(await page.locator('#linkInput').inputValue(), '');
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
  assert.equal(new URL(page.url()).pathname, '/');
  assert.deepEqual(errors, []);
  console.log('Browser smoke checks passed: desktop/mobile, a11y, explicit choice, reset, no storage, no runtime/console errors.');
} finally { await browser?.close(); await new Promise(resolve => server.close(resolve)); }
