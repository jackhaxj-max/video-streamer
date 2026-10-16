import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { parseHandler, mediaHandler, sendJson, privateHeaders } from './lib/handlers.js';

const assets = { '/': ['index.html', 'text/html; charset=utf-8'], '/index.html': ['index.html', 'text/html; charset=utf-8'],
  '/favicon.svg': ['favicon.svg', 'image/svg+xml'], '/app.js': ['app.js', 'text/javascript; charset=utf-8'], '/styles.css': ['styles.css', 'text/css; charset=utf-8'] };
export const server = http.createServer(async (req, res) => {
  const path = new URL(req.url, 'http://internal').pathname;
  if (path === '/api/parse') return parseHandler(req, res);
  if (path === '/api/media') return mediaHandler(req, res);
  if (!assets[path]) return sendJson(res, 404, { success: false, error: 'Not found.' });
  if (!['GET', 'HEAD'].includes(req.method)) return sendJson(res, 405, { error: 'Method not allowed.' });
  try {
    const [file, type] = assets[path];
    const content = await readFile(new URL(file, import.meta.url));
    privateHeaders(res);
    res.setHeader('Content-Type', type);
    res.setHeader('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'");
    res.end(req.method === 'HEAD' ? undefined : content);
  } catch { sendJson(res, 500, { error: 'Unable to load application.' }); }
});
if (process.argv[1] && import.meta.url === new URL(process.argv[1], 'file:').href) {
  const port = Number(process.env.PORT || 3000);
  server.listen(port, '0.0.0.0', () => console.log(`Video Streamer listening on port ${port}`));
}
