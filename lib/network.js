import http from 'node:http';
import https from 'node:https';
import { lookup } from 'node:dns/promises';
import ipaddr from 'ipaddr.js';
import { AppError } from './errors.js';

export function validateRemoteUrl(value) {
  let url;
  try { url = new URL(value); } catch { throw new AppError('Invalid URL.', 400, 'INVALID_URL'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      (url.port && !['80', '443'].includes(url.port))) {
    throw new AppError('Only public HTTP or HTTPS links on standard ports are supported.', 400, 'INVALID_URL');
  }
  return url;
}

export function isPublicAddress(address) {
  try {
    const parsed = ipaddr.process(address);
    return parsed.range() === 'unicast';
  } catch { return false; }
}

// Check every redirect and pin the DNS result to the actual socket (no DNS rebinding).
export async function requestRemote(value, { method = 'GET', headers = {}, body, redirects = 5, signal } = {}) {
  signal?.throwIfAborted();
  const url = validateRemoteUrl(value);
  const hostname = url.hostname.replace(/^\[|\]$/g, '');
  const addresses = await new Promise((resolve, reject) => {
    const onAbort = () => { signal.removeEventListener('abort', onAbort); reject(signal.reason); };
    signal?.addEventListener('abort', onAbort, { once: true });
    lookup(hostname, { all: true }).then(addresses => {
      signal?.removeEventListener('abort', onAbort);
      resolve(addresses);
    }, error => {
      signal?.removeEventListener('abort', onAbort);
      reject(error);
    });
  });
  signal?.throwIfAborted();
  if (!addresses.length || addresses.some(({ address }) => !isPublicAddress(address))) {
    throw new AppError('The link must point to a public internet address.', 400, 'UNSAFE_URL');
  }
  const address = addresses[0];
  const response = await new Promise((resolve, reject) => {
    const req = (url.protocol === 'https:' ? https : http).request(url, {
      method,
      signal,
      headers: { 'User-Agent': 'VideoStreamer/1.0', 'Accept-Encoding': 'identity', ...headers },
      lookup: (_host, options, callback) => options.all
        ? callback(null, [address]) : callback(null, address.address, address.family),
    }, resolve);
    req.setTimeout(20_000, () => req.destroy(new AppError('The provider timed out. Please try again.', 504, 'UPSTREAM_TIMEOUT')));
    req.on('error', reject);
    req.end(body);
  });
  if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
    response.destroy();
    if (!redirects) throw new AppError('Too many provider redirects.', 502);
    // Never forward API credentials across redirects.
    const next = new URL(response.headers.location, url);
    const nextHeaders = { ...headers };
    if (next.origin !== url.origin) {
      delete nextHeaders.Authorization;
      delete nextHeaders['x-api-key'];
    }
    return requestRemote(next, {
      method: response.statusCode === 303 ? 'GET' : method,
      headers: nextHeaders,
      body: response.statusCode === 303 ? undefined : body,
      redirects: redirects - 1,
      signal,
    });
  }
  return response;
}

export async function readText(response, maxBytes = 2 * 1024 * 1024) {
  const chunks = [];
  let bytes = 0;
  const timer = setTimeout(() => response.destroy(new AppError('The provider timed out.', 504)), 20_000);
  try {
    for await (const chunk of response) {
      bytes += chunk.length;
      if (bytes > maxBytes) throw new AppError('Provider response is too large.', 502);
      chunks.push(chunk);
    }
    return Buffer.concat(chunks).toString('utf8');
  } finally { clearTimeout(timer); response.destroy(); }
}
