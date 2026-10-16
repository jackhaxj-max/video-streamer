import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, cp, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import parse from '../api/parse.js';
import media from '../api/media.js';
const exec = promisify(execFile);

test('Vercel explicitly builds browser assets without rewriting API requests to HTML', async () => {
  const config = JSON.parse(await readFile(new URL('../vercel.json', import.meta.url), 'utf8'));
  assert.equal(config.framework, null);
  assert.equal(config.outputDirectory, 'public');
  assert.equal(config.buildCommand, 'npm run build');
  assert.equal(config.rewrites, undefined);
  assert.equal(config.routes, undefined);
  assert.equal(typeof parse, 'function');
  assert.equal(typeof media, 'function');
  const headers = config.headers.find(rule => rule.source === '/(.*)').headers;
  assert.ok(headers.some(h => h.key === 'Cache-Control' && h.value.includes('no-store')));
});

test('static build publishes only browser files, never server code or environment files', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'video-streamer-build-'));
  try {
    for (const path of ['scripts', 'index.html', 'app.js', 'styles.css', 'favicon.svg']) {
      await cp(new URL(`../${path}`, import.meta.url), join(directory, path), { recursive: true });
    }
    await exec(process.execPath, ['scripts/build.mjs'], { cwd: directory });
    assert.deepEqual((await readdir(join(directory, 'public'))).sort(), ['app.js', 'favicon.svg', 'index.html', 'styles.css']);
    assert.match(await readFile(join(directory, 'public', 'index.html'), 'utf8'), /\/app.js/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
