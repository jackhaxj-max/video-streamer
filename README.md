# Linkplay — Video Streamer

A minimal, no-login Diskwala / Terabox share-link viewer with a link box, three short instructions, and explicit **Stream online** and **Download video** choices. Node.js 22+ is required.

## Run

```sh
npm ci
npm start
# Open http://localhost:3000
```

The server binds to `0.0.0.0` and uses `PORT` (default `3000`). The frontend and API must run on the **same origin**. Do not open `index.html` directly or deploy it alone to GitHub Pages: static hosting cannot execute the parser.

To configure authorized provider resolvers:

```sh
cp .env.example .env
# Edit .env, then:
node --env-file=.env server.js
```

Never commit `.env` or place resolver credentials in frontend JavaScript.

## Why the old “Network Error” happened

The previous HTML called `/api/parse`, but its handler was saved as an unrelated root-level JS file. No server, route mapping, or runtime configuration existed. A missing route commonly returns HTML; the frontend then tried to parse that as JSON and mislabeled the failure as a network error.

`server.js` now implements `/api/parse` and `/api/media`; `api/parse.js` and `api/media.js` also export Node-style serverless handlers. Errors distinguish missing API deployment, provider restrictions, invalid links, timeout, and transport failures.

## What link support means

Both providers have validation and resolution paths:

1. **Without a configured resolver:** inspect a public share's `<video>`, video metadata, or explicit JSON media fields for a direct media URL.
2. **With a configured resolver:** send the share to your own or a trusted, authorized resolver using the contract below. This is needed when the share page only exposes an app/login screen or requires provider-specific API resolution.

**This is not a universal bypass or a complete provider API implementation.** Merely accepting a share URL does not mean its video is publicly downloadable. Terabox and Diskwala may require authentication, cookies, app access, or an authorized provider integration. The app does not bypass those restrictions and does not silently forward links to a random public downloader. Resolver services are not bundled. Public extraction and configured adapters are tested with fixtures; real provider playback has not been verified in this environment (provider hosts are unavailable here).

### Resolver contract (same for either provider)

Set `DISKWALA_RESOLVER_URL` and/or `TERABOX_RESOLVER_URL` to a public HTTPS endpoint. Optional `DISKWALA_RESOLVER_KEY` / `TERABOX_RESOLVER_KEY` is sent as `Authorization: Bearer <key>`.

Request:

```http
POST /your-resolver
Content-Type: application/json
Authorization: Bearer <optional-key>

{"url":"https://www.terabox.com/s/example"}
```

Successful HTTP 200 JSON response:

```json
{
  "success": true,
  "downloadUrl": "https://public-media-host.example/video.mp4?signature=...",
  "filename": "video.mp4",
  "sizeBytes": 536870912
}
```

`streamUrl` is accepted instead of `downloadUrl` if it points to the **same original file**, not a lower-resolution preview. `sizeBytes` must be the original file's byte count, not a formatted string or preview size. Do not return independent preview/download URLs under this contract: the original file must determine the 1 GB policy. Resolver responses must return **one file**, not a folder/list of videos. Use an adapter if your provider uses another schema or authentication header.

The returned URL must be directly fetchable by the backend, including HEAD or byte-range requests where possible. Cookie-, referer-, CAPTCHA-, or browser-session-bound media requires an authorized resolver that provides a usable signed URL. Public HTTP(S) addresses and standard ports only; internal addresses, unsafe protocols, and private-network redirects are rejected.

## Size and playback rules

- **Up to and including 1 GB (`1,073,741,824` bytes):** both actions appear. The player makes no media request until Stream online is clicked.
- **Over 1 GB:** Download video only. Streaming is refused by the API as well as hidden in the UI.
- **Unknown size:** download only. A failed size lookup never defaults to a small file.
- Probe the file with HEAD first; if necessary, use a one-byte range and read the **total** in `Content-Range`. Resolver byte metadata is a fallback. At stream time, verify the upstream total again; a changed, oversized, or unverified response is refused.
- Adaptive `.m3u8`/`.mpd` playlists are download-only because a manifest's byte count is not the video's size. This app does not remux playlists to MP4.
- Native browser playback depends on the source codec/container. There is no transcoding. Unsupported videos can still be downloaded.
- `/api/media` proxies bytes with backpressure and Range support; downloads use `Content-Disposition: attachment`, not a cross-origin anchor that might play instead of download.

## No application history

No accounts, database, link history, browser storage, cookies, analytics, service worker, saved videos, or application request logs. Links/results exist in page memory only. Exit & clear, Clear, navigation away, or back/forward-cache restoration releases the player and returns the page to its initial state. Merely switching tabs does not reset playback.

API, assets, and media responses use `Cache-Control: no-store` in the Node server. The share is submitted in a POST body rather than a query string. Media requests use stateless signed tokens expiring after one hour; no token/session database is kept. File bytes pass through memory and are never written to disk. Disconnecting the player closes the upstream media connection.

**Privacy boundaries:** downloads intentionally remain on the user's device. The app cannot erase browser download records, OS/browser caches, provider records, or infrastructure/access logs. Configure your reverse proxy/hosting to disable or redact request/token/body logging and caching; any configured resolver also needs an appropriate privacy policy. Signed tokens are authenticated, not encrypted, and must be treated as temporary bearer links. Reset removes them from the page, but does not revoke copied links before expiry.

## Production deployment

A long-running Node server behind HTTPS is recommended for large downloads. Start with `npm ci --omit=dev && npm start`. Set a stable high-entropy `MEDIA_TOKEN_SECRET` for multi-instance deployments; a single local process uses a random in-memory key when unset. Never expose the Node port without appropriate production protection (HTTPS, request/bandwidth limits, abuse controls).

The `api/` exports are compatible with Node-style serverless routing (e.g. Vercel), but serverless hosts often impose strict response size, streaming, duration, or bandwidth limits that make files over 1 GB impractical. Those wrappers alone do not remove platform limits. Use the Node server for the media endpoint, or adapt downloads to an authorized delivery service that enforces attachment headers and the same size/privacy policy. `MEDIA_TOKEN_SECRET` is required when running under Vercel so tokens survive separate function instances. Configure the host to apply no-store and referrer/security headers to static assets too.

### Deploy this repository on Vercel

The included `vercel.json` explicitly builds just the browser assets into `public/` while Vercel builds `api/parse.js` and `api/media.js` as Node functions. It does not send `/api/*` to `index.html`. The generated `public/` directory is ignored by Git. Do not upload `index.html` alone.

1. Publish these changes to the Git branch deployed by your Vercel project. Changes in the Arena workspace do **not** update the existing production website automatically. For this session, use `arena/45036883-video-streamer` for a preview/PR; the production branch remains a separate deployment decision.
2. In Vercel, use the repository root as **Root Directory**, **Other** as the framework preset, `npm run build` as the build command, and `public` as the output directory. Remove dashboard overrides that conflict with the checked-in configuration. Use a supported Node 22+ runtime.
3. Add a high-entropy `MEDIA_TOKEN_SECRET` to the intended Preview/Production environment using Vercel's environment-variable settings. Set any authorized provider resolver URLs/keys there as well, never in the public files.
4. Trigger a new deployment from the updated code. Redeploying the original commit will retain the original missing API.
5. Open `/api/parse` directly. A **405 JSON** response (`Use POST with a JSON share URL.`) means the route exists and expects POST. A **404**, HTML document, or the old “Video Utility Prototype” homepage means the new app is not the deployment being served.
6. Test the form. A structured resolver/provider error is a different issue from a missing API route and must not be treated as successful link conversion. The >1 GB media-delivery limitations discussed above still apply on Vercel.

The supplied Diskwala example's public page lists a 573.17 MB `video/x-matroska` file and directs users to the official app. This metadata alone is not a downloadable URL. An authorized resolver is still needed if no public media is exposed; even with a usable URL, browser support for Matroska depends on the browser and codecs. Download remains the fallback.

## Checks

```sh
npm test
npm run check
# Linux desktop/mobile Chromium smoke test + axe accessibility audit:
npm run test:browser
```

Tests use mock providers/media and a DOM harness, plus local HTTP integration tests. They cover both providers, resolver errors, exact 1 GB boundary, unknown sizes, HEAD/range fallbacks, server-enforced stream limits, attachment downloads, token tampering/expiry, private-network blocking, explicit playback choice, API failures, reset and navigation cleanup. No live provider success is implied by passing tests.


### Large downloads without a browser redirect

If hosting the UI/parser on Vercel, use a long-running HTTPS Node server for media delivery when function limits are inadequate. Run this same app there, set the **same** `MEDIA_TOKEN_SECRET` in both environments, and add a Vercel **external rewrite** for `/api/media` to that server's `/api/media`. Keep query strings and Range headers intact. This is a server-side proxy, not an HTTP 301/302 or an external browser page. Do not implement this as a client-side redirect. Verify your host's proxy timeout, response-size, caching and bandwidth behavior with a real large file before promising >1 GB downloads.

The reference site's bots, premium plans, promotions, and long SEO sections are intentionally absent. No private backend code or unverified downloader service from that site is used. The no-login promise concerns visitors; any provider resolver credentials belong only in the operator's server environment.

### Browser QA

`npm run test:browser` starts a temporary local server, uses packaged Linux Chromium, runs an automated accessibility check, checks desktop/mobile layouts for overflow, and exercises the choice/reset UI with a mocked parser response. Screenshots go to ignored `test-results/`. It does **not** verify live Diskwala/Terabox playback or guarantee WCAG compliance. The normal `npm test` suite also covers cancellation, stale player failures, unsafe external media URLs, download preflight errors, fake HTML video responses, and HEAD-to-range fallback.
