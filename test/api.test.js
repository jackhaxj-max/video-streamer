import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { Readable } from 'node:stream';
import { parseHandler, mediaHandler } from '../lib/handlers.js';
import { createToken } from '../lib/tokens.js';
import { STREAM_LIMIT } from '../lib/resolve.js';
import { server as appServer } from '../server.js';

async function withServer(handler, fn) {
  const server = http.createServer(handler);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { await fn(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise(resolve => server.close(resolve)); }
}
const example = { mediaUrl: 'https://cdn.example/movie.mp4', filename: 'movie.mp4', sizeBytes: 4, canStream: true, isLargeFile: false, provider: 'diskwala' };
test('parse API returns private, same-origin choice links and refuses non-POST', async () => {
  await withServer((req, res) => parseHandler(req, res, { resolve: async () => example }), async base => {
    assert.equal((await fetch(`${base}/api/parse`)).status, 405);
    const response = await fetch(`${base}/api/parse`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: 'https://diskwala.com/app/x' }) });
    assert.equal(response.status, 200);
    assert.match(response.headers.get('cache-control'), /no-store/);
    assert.equal(response.headers.get('set-cookie'), null);
    const data = await response.json();
    assert.equal(data.canStream, true);
    assert.match(data.streamUrl, /^\/api\/media\?mode=stream/);
    assert.match(data.downloadUrl, /^\/api\/media\?mode=download/);
    const bad = await fetch(base, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{invalid' });
    assert.equal(bad.status, 400);
  });
});
test('download-only parse response contains no stream URL', async () => {
  await withServer((req, res) => parseHandler(req, res, { resolve: async () => ({ ...example, canStream: false, isLargeFile: true, sizeBytes: STREAM_LIMIT + 1 }) }), async base => {
    const response = await fetch(base, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"url":"https://terabox.com/s/x"}' });
    assert.equal((await response.json()).streamUrl, null);
  });
});
test('media proxy streams ranges and forces attachment for downloads', async () => {
  const token = createToken(example);
  await withServer((req, res) => mediaHandler(req, res, { request: async (_url, options) => {
    if (options.headers.Range) {
      assert.equal(options.headers.Range, 'bytes=1-2');
      return Object.assign(Readable.from(['bc']), { statusCode: 206, headers: { 'content-length': '2', 'content-range': 'bytes 1-2/4', 'content-type': 'video/mp4', 'accept-ranges': 'bytes' } });
    }
    return Object.assign(Readable.from(['abcd']), { statusCode: 200, headers: { 'content-length': '4', 'content-type': 'video/mp4' } });
  } }), async base => {
    const stream = await fetch(`${base}/api/media?mode=stream&token=${token}`, { headers: { Range: 'bytes=1-2' } });
    assert.equal(stream.status, 206);
    assert.equal(stream.headers.get('content-range'), 'bytes 1-2/4');
    assert.equal(await stream.text(), 'bc');
    const download = await fetch(`${base}/api/media?mode=download&token=${token}`);
    assert.match(download.headers.get('content-disposition'), /^attachment;/);
    assert.equal(download.headers.get('content-type'), 'application/octet-stream');
    assert.equal(await download.text(), 'abcd');
  });
});
test('server enforces download-only even for hand-edited mode URLs', async () => {
  const token = createToken({ ...example, canStream: false, sizeBytes: STREAM_LIMIT + 1 });
  await withServer((req, res) => mediaHandler(req, res, { request: () => assert.fail('must not fetch media') }), async base => {
    const response = await fetch(`${base}?mode=stream&token=${token}`);
    assert.equal(response.status, 403);
    assert.equal((await response.json()).code, 'DOWNLOAD_ONLY');
  });
});
test('size increase after parsing cannot bypass stream cap', async () => {
  const token = createToken(example);
  await withServer((req, res) => mediaHandler(req, res, { request: async () => Object.assign(Readable.from([]), { statusCode: 206, headers: { 'content-length': '1', 'content-range': `bytes 0-0/${STREAM_LIMIT + 1}` } }) }), async base => {
    const response = await fetch(`${base}?mode=stream&token=${token}`);
    assert.equal(response.status, 403);
    assert.equal((await response.json()).code, 'DOWNLOAD_ONLY');
  });
});
test('actual server serves UI and JSON errors; never exposes source or environment files', async () => {
  await new Promise(resolve => appServer.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${appServer.address().port}`;
  try {
    const home = await fetch(base);
    assert.equal(home.status, 200);
    assert.match(await home.text(), /Linkplay/);
    for (const file of ['/lib/tokens.js', '/.env', '/package.json', '/.git/config']) assert.equal((await fetch(base + file)).status, 404);
    const bad = await fetch(`${base}/api/parse`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"url":"https://evil.example/video"}' });
    assert.equal(bad.status, 400);
    assert.equal((await bad.json()).code, 'UNSUPPORTED_PROVIDER');
  } finally { await new Promise(resolve => appServer.close(resolve)); }
});

test('HEAD download preflight falls back to GET/range when a host refuses HEAD', async () => {
  const token = createToken(example);
  const methods = [];
  await withServer((req, res) => mediaHandler(req, res, { request: async (_url, options) => {
    methods.push(options.method || 'GET');
    if (options.method === 'HEAD') return Object.assign(Readable.from([]), { statusCode: 405, headers: {} });
    assert.equal(options.headers.Range, 'bytes=0-0');
    return Object.assign(Readable.from(['a']), { statusCode: 206, headers: { 'content-length': '1', 'content-range': 'bytes 0-0/4', 'content-type': 'video/mp4' } });
  } }), async base => {
    const response = await fetch(`${base}?mode=download&token=${token}`, { method: 'HEAD' });
    assert.equal(response.ok, true);
    assert.equal(await response.text(), '');
    assert.deepEqual(methods, ['HEAD', 'GET']);
  });
});
test('provider HTML login/error documents are never downloaded as fake video files', async () => {
  const token = createToken(example);
  await withServer((req, res) => mediaHandler(req, res, { request: async () => Object.assign(Readable.from(['<html>Login</html>']), { statusCode: 200, headers: { 'content-type': 'text/html', 'content-length': '18' } }) }), async base => {
    const response = await fetch(`${base}?mode=download&token=${token}`);
    assert.equal(response.status, 422);
    assert.equal(response.headers.get('content-disposition'), null);
    assert.equal((await response.json()).code, 'MEDIA_UNAVAILABLE');
  });
});
