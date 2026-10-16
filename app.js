const byId = id => document.getElementById(id);
const form = byId('linkForm');
const input = byId('linkInput');
const status = byId('status');
const processBtn = byId('processBtn');
const cancelBtn = byId('cancelBtn');
const result = byId('result');
const player = byId('player');
const wrapper = byId('playerWrapper');
const streamBtn = byId('streamBtn');
const downloadBtn = byId('downloadBtn');
const STREAM_LIMIT = 1024 ** 3;
let media = null;
let pending = null;
let generation = 0;
let preparingDownload = false;

function message(text, kind = 'info') {
  status.textContent = text;
  status.dataset.kind = kind;
  status.hidden = !text;
}
function setBusy(busy) {
  form.setAttribute('aria-busy', String(busy));
  processBtn.disabled = busy;
  input.disabled = busy;
  cancelBtn.hidden = !busy;
  processBtn.textContent = busy ? 'Checking link…' : 'Get video →';
}
function clearPlayer() {
  player.pause();
  player.removeAttribute('src');
  player.load();
  wrapper.hidden = true;
}
function reset() {
  generation += 1;
  pending?.abort();
  pending = null;
  clearPlayer();
  media = null;
  result.hidden = true;
  downloadBtn.removeAttribute('href');
  downloadBtn.removeAttribute('download');
  downloadBtn.removeAttribute('aria-disabled');
  preparingDownload = false;
  downloadBtn.querySelector('span').textContent = 'Download video';
  byId('filename').textContent = '';
  byId('fileMeta').textContent = '';
  byId('sizeNotice').textContent = '';
  input.value = '';
  setBusy(false);
  message('');
}
function sizeLabel(bytes) {
  if (!bytes) return 'Size unverified';
  return bytes >= STREAM_LIMIT ? `${(bytes / STREAM_LIMIT).toFixed(2)} GB` : `${(bytes / 1024 ** 2).toFixed(2)} MB`;
}
function localMediaUrl(value, mode) {
  if (typeof value !== 'string') throw new Error('The video service returned an invalid media link. Please try again.');
  const url = new URL(value, window.location.origin);
  if (url.origin !== window.location.origin || url.pathname !== '/api/media' || url.searchParams.get('mode') !== mode) {
    throw new Error('The video service returned an unsafe media link. No external page was opened.');
  }
  return url.pathname + url.search;
}
function apiError(data, fallback) {
  const messages = {
    RESOLVER_REQUIRED: 'This share doesn’t expose a public video link. This site needs a working connection to the file host before it can open this video.',
    SERVER_CONFIGURATION: 'The video service hasn’t finished setup. Please try again once the site is configured.',
  };
  return new Error(messages[data.code] || data.error || fallback);
}
function validateInput(value) {
  let url;
  try { url = new URL(value); } catch { throw new Error('Paste a complete Diskwala or Terabox share link, starting with https://.'); }
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) {
    throw new Error('Paste a public HTTP or HTTPS share link without embedded login details.');
  }
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const url = input.value.trim();
  reset();
  input.value = url;
  try { validateInput(url); } catch (error) { message(error.message, 'error'); input.focus(); return; }
  const version = generation;
  pending = new AbortController();
  const controller = pending;
  // Leave headroom below the deployed function's 60-second limit.
  const timeout = setTimeout(() => controller.abort('timeout'), 55_000);
  setBusy(true);
  message('Finding your video and checking its size…', 'loading');
  try {
    const response = await fetch('/api/parse', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }), signal: controller.signal, cache: 'no-store', redirect: 'error',
    });
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('The video service isn’t available on this deployment. The site owner needs to deploy the API, not just the webpage.');
    }
    let data;
    try { data = await response.json(); } catch { throw new Error('The video service returned an unreadable response. Please try again.'); }
    if (version !== generation) return;
    if (!response.ok || !data?.success) throw apiError(data || {}, 'We couldn’t open this share. Check the link and try again.');
    const downloadUrl = localMediaUrl(data.downloadUrl, 'download');
    const sizeBytes = Number.isSafeInteger(data.sizeBytes) && data.sizeBytes > 0 ? data.sizeBytes : null;
    const isLargeFile = sizeBytes !== null && sizeBytes > STREAM_LIMIT;
    const canStream = data.canStream === true && sizeBytes !== null && !isLargeFile;
    const streamUrl = canStream ? localMediaUrl(data.streamUrl, 'stream') : null;
    media = { ...data, downloadUrl, streamUrl, sizeBytes, canStream, isLargeFile };
    byId('filename').textContent = data.filename || 'Your video';
    byId('fileMeta').textContent = `${data.provider === 'diskwala' ? 'Diskwala' : 'Terabox'} · ${sizeLabel(sizeBytes)}`;
    // Never load video bytes before the user makes a choice.
    streamBtn.hidden = !canStream;
    streamBtn.disabled = false;
    downloadBtn.href = downloadUrl;
    downloadBtn.download = data.filename || 'video';
    byId('sizeNotice').textContent = isLargeFile
      ? 'This file is over 1 GB. Download it to watch; online streaming is disabled.'
      : !sizeBytes
        ? 'We couldn’t confirm the full file size. Download is available; streaming is disabled.'
        : !canStream
          ? 'This format is download-only. Save the file to watch it.'
          : 'Ready when you are. Watch here, or save the video to your device.';
    result.hidden = false;
    message('');
  } catch (error) {
    if (version !== generation) return;
    message(controller.signal.aborted
      ? 'This is taking longer than expected. Please try again.'
      : error instanceof TypeError
        ? 'We can’t reach the video service. Check your connection and try again. The site owner may need to check that the backend is running.'
        : error.message, 'error');
  } finally {
    clearTimeout(timeout);
    if (version === generation) { pending = null; setBusy(false); }
  }
});
streamBtn.addEventListener('click', () => {
  if (!media?.canStream || !media.streamUrl) return;
  const version = generation;
  message('');
  wrapper.hidden = false;
  player.src = media.streamUrl;
  player.play().catch(() => {
    if (version === generation && media) message('Your browser couldn’t start playback. Try the player controls, or download the video to watch it.');
  });
  wrapper.scrollIntoView({ behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' });
});
downloadBtn.addEventListener('click', async event => {
  event.preventDefault();
  if (!media?.downloadUrl || preparingDownload) return;
  const version = generation;
  const current = media;
  preparingDownload = true;
  pending = new AbortController();
  const controller = pending;
  const timeout = setTimeout(() => controller.abort(), 25_000);
  downloadBtn.setAttribute('aria-disabled', 'true');
  downloadBtn.querySelector('span').textContent = 'Preparing…';
  message('Checking the download link…', 'loading');
  try {
    // Check failures without navigating the user to a JSON/error page.
    const response = await fetch(current.downloadUrl, { method: 'HEAD', cache: 'no-store', signal: controller.signal, redirect: 'error' });
    if (version !== generation) return;
    if (!response.ok) {
      // HEAD has no body, so do not attempt response.json().
      throw new Error(response.status === 410
        ? 'This link expired. Get the video again to download it.'
        : 'The download isn’t available right now. Get the video again, or try another share.');
    }
    if (!response.headers.get('content-disposition')?.startsWith('attachment;')) {
      throw new Error('The download service didn’t return a file. No extra page was opened. Please try again later.');
    }
    const anchor = document.createElement('a');
    anchor.href = current.downloadUrl;
    anchor.download = current.filename || 'video';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    message('Download requested. Check your browser’s downloads. The file is saved only to your device.');
  } catch (error) {
    if (version !== generation) return;
    message(controller.signal.aborted ? 'The download check timed out. Please try again.' : error.message, 'error');
  } finally {
    clearTimeout(timeout);
    if (version === generation) {
      pending = null;
      preparingDownload = false;
      downloadBtn.removeAttribute('aria-disabled');
      downloadBtn.querySelector('span').textContent = 'Download video';
    }
  }
});
player.addEventListener('error', () => {
  if (!media || !player.hasAttribute('src')) return;
  message('This video couldn’t be played. The link may have expired or your browser may not support its format. Download it, or get the video again.', 'error');
});
const clearAndFocus = () => { reset(); input.focus(); };
byId('exitBtn').addEventListener('click', clearAndFocus);
byId('resetBtn').addEventListener('click', clearAndFocus);
cancelBtn.addEventListener('click', clearAndFocus);
// No localStorage, sessionStorage, cookies, analytics, or URL/history updates.
window.addEventListener('pagehide', reset);
window.addEventListener('pageshow', event => { if (event.persisted) reset(); });
reset();
