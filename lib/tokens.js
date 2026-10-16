import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { AppError } from './errors.js';
const ephemeralKey = randomBytes(32).toString('hex');
function secret() {
  if (process.env.VERCEL && !process.env.MEDIA_TOKEN_SECRET) {
    throw new AppError('Set MEDIA_TOKEN_SECRET in the deployment environment.', 503, 'SERVER_CONFIGURATION');
  }
  return process.env.MEDIA_TOKEN_SECRET || ephemeralKey;
}
function sign(payload) { return createHmac('sha256', secret()).update(payload).digest('base64url'); }
export function createToken(media, now = Date.now()) {
  const payload = Buffer.from(JSON.stringify({ ...media, exp: now + 60 * 60 * 1000 })).toString('base64url');
  return `${payload}.${sign(payload)}`;
}
export function verifyToken(token, now = Date.now()) {
  const [payload, signature, extra] = String(token || '').split('.');
  if (!payload || !signature || extra || signature.length !== 43) throw new AppError('Invalid media link. Process the share again.', 403);
  const expected = Buffer.from(sign(payload));
  const actual = Buffer.from(signature);
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) throw new AppError('Invalid media link.', 403);
  let data;
  try { data = JSON.parse(Buffer.from(payload, 'base64url').toString()); } catch { throw new AppError('Invalid media link.', 403); }
  if (!Number.isFinite(data.exp) || data.exp <= now) throw new AppError('This media link expired. Process the share again.', 410, 'LINK_EXPIRED');
  return data;
}
