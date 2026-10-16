import { pipeline } from 'node:stream/promises';
import { AppError } from './errors.js';
import { resolveShare, STREAM_LIMIT, positiveBytes } from './resolve.js';
import { createToken, verifyToken } from './tokens.js';
import { requestRemote } from './network.js';

export function privateHeaders(res) {
  res.setHeader('Cache-Control', 'no-store, max-age=0');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Content-Type-Options', 'nosniff');
}
export function sendJson(res, status, data) {
  privateHeaders(res);
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(data));
}
export function sendError(res, error) {
  if (res.headersSent) { res.destroy(); return; }
  const known = error instanceof AppError;
  sendJson(res, known ? error.status : 502, { success: false,
    code: known ? error.code : 'UPSTREAM_NETWORK_ERROR',
    error: known ? error.message : 'Unable to reach the provider. It may be unavailable or blocking requests. Please try again later.' });
}
async function readBody(req) {
  // Serverless platforms may have parsed the body already.
  if (req.body !== undefined) {
    if (typeof req.body === 'string') {
      try { return JSON.parse(req.body); } catch { throw new AppError('Invalid JSON body.', 400, 'INVALID_REQUEST'); }
    }
    return req.body;
  }
  let body = '';
  for await (const chunk of req) {
    body += chunk;
    if (Buffer.byteLength(body) > 8192) throw new AppError('Request is too large.', 413);
  }
  try { return JSON.parse(body); } catch { throw new AppError('Send a JSON body containing a share URL.', 400, 'INVALID_REQUEST'); }
}
export async function parseHandler(req, res, { resolve = resolveShare } = {}) {
  const deadline = AbortSignal.timeout(50_000);
  privateHeaders(res);
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return sendJson(res, 405, { success: false, error: 'Use POST with a JSON share URL.' });
  }
  try {
    if (!req.headers['content-type']?.includes('application/json')) throw new AppError('Content-Type must be application/json.', 415);
    const body = await readBody(req);
    if (typeof body?.url !== 'string' || body.url.length > 4096) throw new AppError('Enter a valid share link.', 400, 'INVALID_URL');
    const media = await resolve(body.url, { signal: deadline });
    const token = createToken(media);
    sendJson(res, 200, {
      success: true, provider: media.provider, filename: media.filename,
      sizeBytes: media.sizeBytes, isLargeFile: media.isLargeFile, canStream: media.canStream,
      streamUrl: media.canStream ? `/api/media?mode=stream&token=${token}` : null,
      downloadUrl: `/api/media?mode=download&token=${token}`,
    });
  } catch (error) {
    sendError(res, deadline.aborted
      ? new AppError('The file host took too long to respond. Please try again.', 504, 'UPSTREAM_TIMEOUT')
      : error);
  }
}

export async function mediaHandler(req, res, { request = requestRemote } = {}) {
  privateHeaders(res);
  if (!['GET', 'HEAD'].includes(req.method)) {
    res.setHeader('Allow', 'GET, HEAD');
    return sendJson(res, 405, { success: false, error: 'Method not allowed.' });
  }
  let upstream;
  try {
    const params = new URL(req.url, 'http://internal').searchParams;
    const media = verifyToken(params.get('token'));
    const mode = params.get('mode');
    if (!['stream', 'download'].includes(mode)) throw new AppError('Invalid media mode.', 400);
    if (mode === 'stream' && (!media.canStream || !media.sizeBytes || media.sizeBytes > STREAM_LIMIT)) {
      throw new AppError('This file is download-only.', 403, 'DOWNLOAD_ONLY');
    }
    const range = req.headers.range;
    if (range && !/^bytes=(?:\d+-\d*|-\d+)$/.test(range)) throw new AppError('Only one byte range is supported.', 416);
    upstream = await request(media.mediaUrl, { method: req.method, headers: range ? { Range: range } : {} });
    if (req.method === 'HEAD' && [403, 405, 501].includes(upstream.statusCode)) {
      upstream.destroy();
      upstream = await request(media.mediaUrl, { headers: { Range: 'bytes=0-0' } });
    }
    if (![200, 206].includes(upstream.statusCode)) {
      throw new AppError('The provider refused the file request. Its direct link may have expired; process the share again.', 502, 'MEDIA_UNAVAILABLE');
    }
    if (mode === 'stream') {
      const total = upstream.statusCode === 206
        ? positiveBytes(upstream.headers['content-range']?.match(/^bytes \d+-\d+\/(\d+)$/)?.[1])
        : positiveBytes(upstream.headers['content-length']);
      if (!total || total > STREAM_LIMIT) throw new AppError('File size could not be confirmed below the streaming limit. Please download instead.', 403, 'DOWNLOAD_ONLY');
    }
    res.statusCode = upstream.statusCode;
    for (const header of ['content-length', 'content-range', 'accept-ranges']) {
      if (upstream.headers[header]) res.setHeader(header, upstream.headers[header]);
    }
    const type = upstream.headers['content-type'] || 'application/octet-stream';
    if (/^(text\/html|application\/(?:json|xhtml\+xml))/i.test(type)) {
      throw new AppError('The provider returned a webpage instead of the video. Get the video again or try another share.', 422, 'MEDIA_UNAVAILABLE');
    }
    if (mode === 'stream' && !/^(video\/|audio\/|application\/octet-stream)/i.test(type)) {
      throw new AppError('The provider did not return a playable media file. Try downloading or process the share again.', 422);
    }
    res.setHeader('Content-Type', mode === 'download' ? 'application/octet-stream' : type);
    res.setHeader('Content-Disposition', `${mode === 'download' ? 'attachment' : 'inline'}; filename*=UTF-8''${encodeURIComponent(media.filename).replace(/['()]/g, char => `%${char.charCodeAt(0).toString(16)}`)}`);
    if (req.method === 'HEAD') { upstream.destroy(); res.end(); return; }
    // Backpressure + abort on browser disconnect. Nothing is written to disk.
    res.on('close', () => upstream.destroy());
    await pipeline(upstream, res);
  } catch (error) {
    upstream?.destroy();
    // Clear media headers before returning a JSON error.
    if (!res.headersSent) for (const header of ['Content-Length', 'Content-Range', 'Accept-Ranges', 'Content-Disposition']) res.removeHeader(header);
    sendError(res, error);
  }
}
