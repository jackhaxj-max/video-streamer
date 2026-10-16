import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const script = await readFile(new URL('../app.js', import.meta.url), 'utf8');
const small = { success: true, provider: 'terabox', filename: 'my-video.mp4', canStream: true, sizeBytes: 512 * 1024 ** 2,
  isLargeFile: false, streamUrl: '/api/media?mode=stream&token=test', downloadUrl: '/api/media?mode=download&token=test' };
const reply = (data, { ok = true, json = true } = {}) => ({ ok, status: ok ? 200 : 422,
  headers: new Map([['content-type', json ? 'application/json' : 'text/html']]), json: async () => data });
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup(fetchImpl = async () => reply(small)) {
  const dom = new JSDOM(html, { url: 'https://video.example/', runScripts: 'outside-only' });
  const { window } = dom;
  window.HTMLMediaElement.prototype.pause = () => {};
  window.HTMLMediaElement.prototype.load = () => {};
  window.HTMLMediaElement.prototype.play = () => Promise.resolve();
  window.HTMLElement.prototype.scrollIntoView = () => {};
  window.fetch = fetchImpl;
  window.eval(script);
  const get = id => window.document.getElementById(id);
  const submit = () => {
    get('linkInput').value = 'https://terabox.com/s/example';
    get('linkForm').dispatchEvent(new window.Event('submit', { cancelable: true }));
  };
  return { window, get, submit, close: () => window.close() };
}
test('small videos offer a choice without starting a stream; Exit clears all session data', async () => {
  let request;
  const ui = setup(async (url, options) => { request = { url, options }; return reply(small); });
  try {
    ui.submit();
    await tick();
    assert.equal(request.url, '/api/parse');
    assert.equal(request.options.method, 'POST');
    assert.equal(ui.get('result').hidden, false);
    assert.equal(ui.get('streamBtn').hidden, false);
    assert.equal(ui.get('player').hasAttribute('src'), false);
    ui.get('streamBtn').click();
    assert.equal(ui.get('playerWrapper').hidden, false);
    assert.match(ui.get('player').src, /mode=stream/);
    ui.get('exitBtn').click();
    assert.equal(ui.get('result').hidden, true);
    assert.equal(ui.get('playerWrapper').hidden, true);
    assert.equal(ui.get('player').hasAttribute('src'), false);
    assert.equal(ui.get('downloadBtn').hasAttribute('href'), false);
    assert.equal(ui.get('linkInput').value, '');
    assert.equal(ui.window.localStorage.length, 0);
    assert.equal(ui.window.sessionStorage.length, 0);
    assert.equal(ui.window.document.cookie, '');
    assert.equal(ui.window.location.href, 'https://video.example/');
    assert.equal(ui.window.history.length, 1);
  } finally { ui.close(); }
});
test('large and unknown-size videos expose download only', async () => {
  for (const data of [{ ...small, sizeBytes: 1024 ** 3 + 1, isLargeFile: true }, { ...small, sizeBytes: null }]) {
    const ui = setup(async () => reply({ ...data, canStream: false, streamUrl: null }));
    try {
      ui.submit(); await tick();
      assert.equal(ui.get('streamBtn').hidden, true);
      assert.match(ui.get('downloadBtn').href, /mode=download/);
      assert.equal(ui.get('playerWrapper').hidden, true);
      assert.equal(ui.get('player').hasAttribute('src'), false);
    } finally { ui.close(); }
  }
});
test('static-host HTML and provider errors are not mislabeled as network failures', async () => {
  for (const [response, expected] of [
    [reply(null, { json: false }), /deploy the API/],
    [reply({ success: false, error: 'Share requires login' }, { ok: false }), /Share requires login/],
  ]) {
    const ui = setup(async () => response);
    try {
      ui.submit(); await tick();
      assert.match(ui.get('status').textContent, expected);
      assert.equal(ui.get('status').dataset.kind, 'error');
      assert.equal(ui.get('processBtn').disabled, false);
      assert.equal(ui.get('result').hidden, true);
    } finally { ui.close(); }
  }
});
test('navigation clears data and stale API responses cannot restore it', async () => {
  let finish;
  const ui = setup(() => new Promise(resolve => { finish = resolve; }));
  try {
    ui.submit();
    ui.window.dispatchEvent(new ui.window.Event('pagehide'));
    finish(reply(small)); await tick();
    assert.equal(ui.get('result').hidden, true);
    assert.equal(ui.get('linkInput').value, '');
    assert.equal(ui.get('processBtn').disabled, false);
    assert.equal(ui.get('downloadBtn').hasAttribute('href'), false);
  } finally { ui.close(); }
});
test('back-forward cache restoration resets a previously resolved link', async () => {
  const ui = setup();
  try {
    ui.submit(); await tick();
    assert.equal(ui.get('result').hidden, false);
    ui.window.dispatchEvent(new ui.window.PageTransitionEvent('pageshow', { persisted: true }));
    assert.equal(ui.get('result').hidden, true);
    assert.equal(ui.get('linkInput').value, '');
  } finally { ui.close(); }
});
test('a dropped API connection displays an actionable error and re-enables the form', async () => {
  const ui = setup();
  ui.window.fetch = async () => { throw new ui.window.TypeError('Failed to fetch'); };
  try {
    ui.submit(); await tick();
    assert.match(ui.get('status').textContent, /backend is running/);
    assert.equal(ui.get('processBtn').disabled, false);
    assert.equal(ui.get('linkInput').disabled, false);
  } finally { ui.close(); }
});

test('the default page has no outbound links, accounts, bots, redirects, or external assets', () => {
  const ui = setup();
  try {
    assert.equal(ui.window.document.querySelectorAll('a[href], iframe, [target="_blank"]').length, 0);
    for (const node of ui.window.document.querySelectorAll('script[src], link[href]')) {
      assert.equal(new URL(node.getAttribute('src') || node.getAttribute('href'), ui.window.location).origin, ui.window.location.origin);
    }
    assert.equal(ui.window.document.querySelectorAll('form').length, 1);
    assert.equal(ui.window.document.querySelectorAll('input').length, 1);
  } finally { ui.close(); }
});
test('Cancel aborts the pending request and returns to the clean input state', async () => {
  let signal;
  const ui = setup((_url, options) => {
    signal = options.signal;
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))));
  });
  try {
    ui.submit();
    assert.equal(ui.get('cancelBtn').hidden, false);
    assert.equal(ui.get('linkForm').getAttribute('aria-busy'), 'true');
    ui.get('cancelBtn').click(); await tick();
    assert.equal(signal.aborted, true);
    assert.equal(ui.get('cancelBtn').hidden, true);
    assert.equal(ui.get('linkInput').value, '');
    assert.equal(ui.get('status').hidden, true);
    assert.equal(ui.get('processBtn').disabled, false);
  } finally { ui.close(); }
});
test('unsafe/outbound media responses never expose a redirect to another site', async () => {
  for (const downloadUrl of ['https://other.example/file', 'javascript:alert(1)', '/other-page']) {
    const ui = setup(async () => reply({ ...small, downloadUrl }));
    try {
      ui.submit(); await tick();
      assert.equal(ui.get('result').hidden, true);
      assert.equal(ui.get('downloadBtn').hasAttribute('href'), false);
      assert.equal(ui.get('status').dataset.kind, 'error');
      assert.equal(ui.window.location.href, 'https://video.example/');
    } finally { ui.close(); }
  }
});
test('client independently prevents streaming files over 1 GB even if an API flag is wrong', async () => {
  const ui = setup(async () => reply({ ...small, sizeBytes: 1024 ** 3 + 1, canStream: true }));
  try {
    ui.submit(); await tick();
    assert.equal(ui.get('streamBtn').hidden, true);
    ui.get('streamBtn').click();
    assert.equal(ui.get('player').hasAttribute('src'), false);
  } finally { ui.close(); }
});
test('download errors leave the visitor on the same page and never follow an error redirect', async () => {
  const ui = setup(async (_url, options) => options.method === 'POST' ? reply(small) : { ok: false, status: 410 });
  let navigations = 0;
  ui.window.HTMLAnchorElement.prototype.click = () => { navigations++; };
  try {
    ui.submit(); await tick();
    ui.get('downloadBtn').dispatchEvent(new ui.window.MouseEvent('click', { bubbles: true, cancelable: true })); await tick();
    assert.match(ui.get('status').textContent, /link expired/);
    assert.equal(navigations, 0);
    assert.equal(ui.get('result').hidden, false);
    assert.equal(ui.get('downloadBtn').hasAttribute('aria-disabled'), false);
  } finally { ui.close(); }
});
test('a checked download uses a same-origin attachment without new tabs', async () => {
  const ui = setup(async (_url, options) => options.method === 'POST' ? reply(small) : { ok: true, status: 200, headers: new Map([['content-disposition', 'attachment; filename=video.mp4']]) });
  let attachment;
  ui.window.HTMLAnchorElement.prototype.click = function () { attachment = { href: this.href, name: this.download, target: this.target }; };
  try {
    ui.submit(); await tick();
    ui.get('downloadBtn').dispatchEvent(new ui.window.MouseEvent('click', { bubbles: true, cancelable: true })); await tick();
    assert.match(attachment.href, /^https:\/\/video.example\/api\/media/);
    assert.equal(attachment.name, 'my-video.mp4');
    assert.equal(attachment.target, '');
    assert.match(ui.get('status').textContent, /Download requested/);
  } finally { ui.close(); }
});
test('late player failures cannot repopulate a cleared page', async () => {
  const ui = setup();
  let rejectPlayback;
  ui.window.HTMLMediaElement.prototype.play = () => new Promise((_resolve, reject) => { rejectPlayback = reject; });
  try {
    ui.submit(); await tick();
    ui.get('streamBtn').click();
    ui.get('exitBtn').click();
    rejectPlayback(new Error('late failure')); await tick();
    assert.equal(ui.get('status').hidden, true);
    assert.equal(ui.get('result').hidden, true);
  } finally { ui.close(); }
});

test('an HTML/login fallback with HTTP 200 is not treated as a downloadable video', async () => {
  const ui = setup(async (_url, options) => options.method === 'POST' ? reply(small) : { ok: true, status: 200, headers: new Map([['content-type', 'text/html']]) });
  let navigations = 0;
  ui.window.HTMLAnchorElement.prototype.click = () => { navigations++; };
  try {
    ui.submit(); await tick();
    ui.get('downloadBtn').dispatchEvent(new ui.window.MouseEvent('click', { bubbles: true, cancelable: true })); await tick();
    assert.equal(navigations, 0);
    assert.match(ui.get('status').textContent, /No extra page was opened/);
  } finally { ui.close(); }
});
