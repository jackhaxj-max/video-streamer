import { load } from 'cheerio';
import { AppError } from './errors.js';
import { requestRemote, readText, validateRemoteUrl } from './network.js';

export const STREAM_LIMIT = 1024 ** 3;
const providers = {
  diskwala: ['diskwala.com'],
  terabox: ['terabox.com', 'terabox.app', 'terabox.link', 'teraboxshare.com', '1024terabox.com',
    '1024tera.com', 'terasharelink.com', 'terafileshare.com', 'teraboxurl.com', 'freeterabox.com',
    'dubox.com', '4funbox.com', 'mirrobox.com', 'nephobox.com', 'momerybox.com', 'tibibox.com'],
};
export function parseShareUrl(value) {
  const url = validateRemoteUrl(value);
  const provider = Object.keys(providers).find(key => providers[key].some(domain =>
    url.hostname === domain || url.hostname.endsWith(`.${domain}`)));
  if (!provider) throw new AppError('Paste a Diskwala or Terabox share link.', 400, 'UNSUPPORTED_PROVIDER');
  if (url.pathname === '/' && !url.search) throw new AppError('Paste a file share link, not the provider homepage.', 400, 'INVALID_URL');
  url.hash = '';
  return { url: url.href, provider };
}

export function positiveBytes(value) {
  if (typeof value !== 'string' && typeof value !== 'number') return null;
  if (typeof value === 'string' && !/^\d+$/.test(value)) return null;
  const n = Number(value);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

export function mediaPolicy(sizeBytes) {
  const size = positiveBytes(sizeBytes);
  return { sizeBytes: size, isLargeFile: size !== null && size > STREAM_LIMIT,
    canStream: size !== null && size <= STREAM_LIMIT };
}

function decodeUrl(value) {
  return value?.replace(/\\u002[fF]/g, '/').replace(/\\u0026/g, '&').replace(/\\\//g, '/').replace(/&amp;/g, '&');
}

// Deliberately only use explicit media fields, not arbitrary .mp4 links (e.g. advertisements).
export function extractPublicMedia(html) {
  const $ = load(html);
  let mediaUrl = $('video[src], video source[src]').first().attr('src') ||
    $('meta[property="og:video:url"], meta[property="og:video"], meta[property="og:video:secure_url"]').first().attr('content');
  const name = $('meta[property="og:title"]').attr('content') || $('title').text();
  if (!mediaUrl) {
    const match = html.match(/"(?:playUrl|streamUrl|downloadUrl|dlink|contentUrl)"\s*:\s*"((?:\\.|[^"\\])+)"/i);
    if (match) mediaUrl = decodeUrl(match[1]);
  }
  return { mediaUrl: decodeUrl(mediaUrl), name: name?.trim() || 'video' };
}

async function probeSize(url, request) {
  let response;
  try {
    response = await request(url, { method: 'HEAD' });
    if (response.statusCode >= 200 && response.statusCode < 300) {
      const size = positiveBytes(response.headers['content-length']);
      if (size) return size;
    }
  } catch { /* A range probe may still work when HEAD is blocked. */ }
  finally { response?.destroy(); }
  try {
    response = await request(url, { headers: { Range: 'bytes=0-0' } });
    if (response.statusCode === 206) {
      return positiveBytes(response.headers['content-range']?.match(/^bytes \d+-\d+\/(\d+)$/)?.[1]);
    }
    if (response.statusCode === 200) return positiveBytes(response.headers['content-length']);
  } catch { /* Unknown size is download-only. */ }
  finally { response?.destroy(); }
  return null;
}

export async function resolveShare(value, { request = requestRemote, env = process.env, signal } = {}) {
  const remote = signal ? (target, options = {}) => request(target, { ...options, signal }) : request;
  const { url, provider } = parseShareUrl(value);
  const prefix = provider.toUpperCase();
  const endpoint = env[`${prefix}_RESOLVER_URL`];
  let media;
  if (endpoint) {
    validateRemoteUrl(endpoint);
    const key = env[`${prefix}_RESOLVER_KEY`];
    const response = await remote(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) },
      body: JSON.stringify({ url }),
    });
    if (response.statusCode !== 200) {
      response.destroy();
      throw new AppError(`${provider} resolver failed. Check its configuration or try another share.`, 502, 'RESOLVER_UNAVAILABLE');
    }
    let data;
    try { data = JSON.parse(await readText(response)); }
    catch { throw new AppError('The configured resolver returned an invalid JSON response.', 502, 'INVALID_RESOLVER_RESPONSE'); }
    if (data.success === false || !(data.downloadUrl || data.streamUrl)) {
      throw new AppError('The resolver could not obtain a public file. The share may be expired, private, or password-protected.', 422, 'SHARE_UNAVAILABLE');
    }
    media = { mediaUrl: data.downloadUrl || data.streamUrl, name: data.filename || 'video', sizeBytes: positiveBytes(data.sizeBytes) };
  } else {
    const response = await remote(url);
    if (response.statusCode !== 200) {
      response.destroy();
      throw new AppError('The share is unavailable or requires provider authentication.', 422, 'SHARE_UNAVAILABLE');
    }
    media = extractPublicMedia(await readText(response));
    if (!media.mediaUrl) {
      throw new AppError(`This ${provider === 'diskwala' ? 'Diskwala' : 'Terabox'} share does not expose a public video URL. It may require the official app or login. The site administrator can configure a ${prefix}_RESOLVER_URL for authorized resolution.`, 422, 'RESOLVER_REQUIRED');
    }
  }
  const mediaUrl = validateRemoteUrl(new URL(media.mediaUrl, url).href).href;
  // Prefer the actual file's size over share-page metadata. Never infer a small size.
  const verifiedSize = await probeSize(mediaUrl, remote);
  signal?.throwIfAborted();
  const policy = mediaPolicy(verifiedSize ?? media.sizeBytes);
  // Adaptive playlists don't represent the full video's length in bytes: download-only.
  const playlist = /\.(?:m3u8|mpd)(?:$|[?#])/i.test(mediaUrl);
  return { ...policy, canStream: policy.canStream && !playlist, mediaUrl,
    provider, filename: String(media.name).replace(/[\r\n\\/\x00-\x1f]/g, '_').slice(0, 180) || 'video' };
}
