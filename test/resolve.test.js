import test from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { parseShareUrl, extractPublicMedia, resolveShare, mediaPolicy, STREAM_LIMIT, positiveBytes } from '../lib/resolve.js';
import { isPublicAddress, validateRemoteUrl, requestRemote } from '../lib/network.js';
import { createToken, verifyToken } from '../lib/tokens.js';

function response(body = '', headers = {}, statusCode = 200) {
  return Object.assign(Readable.from([Buffer.from(body)]), { headers, statusCode });
}
test('recognizes both providers and common Terabox share domains, not lookalikes', () => {
  for (const host of ['diskwala.com', 'www.diskwala.com', 'terabox.com', '1024terabox.com', 'teraboxlink.terabox.com', 'terasharelink.com']) {
    assert.ok(parseShareUrl(`https://${host}/s/abc`).provider);
  }
  for (const url of ['https://diskwala.com.evil.com/s/x', 'https://notterabox.com/s/x', 'ftp://terabox.com/s/x', 'https://terabox.com/', 'https://u:p@diskwala.com/app/x', 'invalid']) {
    assert.throws(() => parseShareUrl(url));
  }
});
test('1 GB threshold is inclusive and unknown or invalid sizes are download-only', () => {
  assert.equal(mediaPolicy(STREAM_LIMIT).canStream, true);
  assert.equal(mediaPolicy(STREAM_LIMIT + 1).canStream, false);
  assert.equal(mediaPolicy(STREAM_LIMIT + 1).isLargeFile, true);
  for (const size of [null, undefined, '', '0', 0, -2, '120 MB', true, Infinity]) assert.equal(mediaPolicy(size).canStream, false);
  assert.equal(positiveBytes('12345'), 12345);
});
test('extracts public media from video, metadata, and escaped JSON fields', () => {
  assert.equal(extractPublicMedia('<title>My film</title><video><source src="/video.mp4?x=1&amp;y=2"></video>').mediaUrl, '/video.mp4?x=1&y=2');
  assert.equal(extractPublicMedia('<meta property="og:video" content="https://cdn.example/a.mp4">').mediaUrl, 'https://cdn.example/a.mp4');
  assert.equal(extractPublicMedia(String.raw`<script>{"playUrl":"https:\/\/cdn.example\/v.mp4?a=1\u0026b=2"}</script>`).mediaUrl, 'https://cdn.example/v.mp4?a=1&b=2');
  assert.equal(extractPublicMedia('<a href="https://ad.example/promo.mp4">Ad</a>').mediaUrl, undefined);
});
test('public page resolves without a configured service, checks size before offering a choice', async () => {
  const calls = [];
  const result = await resolveShare('https://diskwala.com/app/abc', { env: {}, request: async (url, options) => {
    calls.push([url, options]);
    return options?.method === 'HEAD' ? response('', { 'content-length': '1024' })
      : response('<title>Example video</title><video src="https://cdn.example/video.mp4"></video>');
  } });
  assert.equal(result.canStream, true);
  assert.equal(result.filename, 'Example video');
  assert.equal(result.sizeBytes, 1024);
  assert.equal(calls.length, 2);
});
test('HEAD failure falls back to total range size, not the 1-byte partial length', async () => {
  const result = await resolveShare('https://terabox.com/s/abc', { env: {}, request: async (_url, options) => {
    if (!options) return response('<video src="https://cdn.example/file.mp4"></video>');
    if (options.method === 'HEAD') return response('', {}, 405);
    assert.equal(options.headers.Range, 'bytes=0-0');
    return response('x', { 'content-length': '1', 'content-range': `bytes 0-0/${STREAM_LIMIT + 1}` }, 206);
  } });
  assert.equal(result.canStream, false);
  assert.equal(result.isLargeFile, true);
});
test('missing size is never streamed and playlists remain download-only', async () => {
  for (const ext of ['mp4', 'm3u8']) {
    const result = await resolveShare('https://diskwala.com/app/abc', { env: {}, request: async (_url, options) => {
      if (!options) return response(`<video src="https://cdn.example/file.${ext}"></video>`);
      return response('', ext === 'm3u8' ? { 'content-length': '100' } : {});
    } });
    assert.equal(result.canStream, false);
  }
});
test('both provider resolver adapters POST shares and keep credentials server-side', async () => {
  for (const provider of ['DISKWALA', 'TERABOX']) {
    const result = await resolveShare(`https://${provider.toLowerCase()}.com/s/abc`, {
      env: { [`${provider}_RESOLVER_URL`]: 'https://resolver.example/resolve', [`${provider}_RESOLVER_KEY`]: 'secret' },
      request: async (url, options) => {
        if (url === 'https://resolver.example/resolve') {
          assert.equal(options.method, 'POST');
          assert.equal(options.headers.Authorization, 'Bearer secret');
          assert.match(JSON.parse(options.body).url, /\/s\/abc$/);
          return response(JSON.stringify({ downloadUrl: 'https://cdn.example/file.mp4', filename: 'movie.mp4', sizeBytes: STREAM_LIMIT + 100 }));
        }
        // Actual media header must override a resolver's metadata.
        return response('', { 'content-length': '1000' });
      },
    });
    assert.equal(result.sizeBytes, 1000);
    assert.equal(result.canStream, true);
  }
});
test('restricted pages and invalid resolver responses return useful errors', async () => {
  await assert.rejects(resolveShare('https://terabox.com/s/abc', { env: {}, request: async () => response('<html>Login required</html>') }), { code: 'RESOLVER_REQUIRED' });
  await assert.rejects(resolveShare('https://diskwala.com/app/x', { env: { DISKWALA_RESOLVER_URL: 'https://resolver.example/' }, request: async () => response('<html>Bad gateway</html>') }), { code: 'INVALID_RESOLVER_RESPONSE' });
});
test('blocks local/private networks, IPv4-mapped IPv6, unsafe schemes and ports', async () => {
  for (const ip of ['127.0.0.1', '10.1.2.3', '172.16.0.1', '192.168.0.1', '169.254.169.254', '100.64.0.1', '::1', 'fc00::1', 'fe80::1', '::ffff:127.0.0.1']) assert.equal(isPublicAddress(ip), false, ip);
  assert.equal(isPublicAddress('8.8.8.8'), true);
  assert.throws(() => validateRemoteUrl('file:///etc/passwd'));
  assert.throws(() => validateRemoteUrl('https://example.com:8080/'));
  await assert.rejects(requestRemote('http://127.0.0.1/'), { code: 'UNSAFE_URL' });
});
test('stateless media tokens reject tampering and expiry', () => {
  const token = createToken({ mediaUrl: 'https://cdn.example/v.mp4', canStream: false }, 1000);
  assert.equal(verifyToken(token, 2000).canStream, false);
  assert.throws(() => verifyToken(token, 3_601_000), { code: 'LINK_EXPIRED' });
  const [payload, sig] = token.split('.');
  assert.throws(() => verifyToken(`${payload}.${sig[0] === 'a' ? 'b' : 'a'}${sig.slice(1)}`, 2000));
  assert.throws(() => verifyToken('garbage'));
});

test('an aborted parsing request does not start a network connection', async () => {
  const controller = new AbortController();
  controller.abort(new Error('Parsing deadline exceeded'));
  await assert.rejects(requestRemote('https://github.com', { signal: controller.signal }), /Parsing deadline exceeded/);
});
