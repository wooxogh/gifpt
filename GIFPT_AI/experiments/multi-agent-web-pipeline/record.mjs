// Headless recorder for multi-agent web animation pipeline.
// Loads HTML in Chromium, captures keyframe screenshots during animation,
// waits for window.__animationDone__, saves WebM video.
//
// Usage:
//   node record.mjs <html-path> <output-dir>
//
// Outputs into <output-dir>:
//   video.webm                — full recording
//   frame_0.png … frame_N.png — keyframe snapshots (for Critic agent)
//   console_errors.json       — array of console + page errors (if any)

import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const [, , htmlArg, outDirArg] = process.argv;
if (!htmlArg || !outDirArg) {
  console.error('usage: node record.mjs <html-path> <output-dir>');
  process.exit(2);
}

const HTML_PATH = path.resolve(htmlArg);
const OUT_DIR = path.resolve(outDirArg);
const MAX_WAIT_MS = 90_000;
const TAIL_BUFFER_MS = 600;
// Keyframe snapshot times (ms from start). Tuned for 50s animations; for shorter
// scenes, later snaps will fall on the end-state which is still useful to Critic.
const SNAP_OFFSETS_MS = [4_000, 14_000, 24_000, 34_000, 44_000];

if (!fs.existsSync(HTML_PATH)) {
  console.error(`html not found: ${HTML_PATH}`);
  process.exit(2);
}
fs.mkdirSync(OUT_DIR, { recursive: true });

// Clean stale outputs so failed runs don't masquerade as success
for (const f of fs.readdirSync(OUT_DIR)) {
  if (f === 'video.webm' || f === 'console_errors.json' || f.match(/^frame_\d+\.png$/)) {
    fs.unlinkSync(path.join(OUT_DIR, f));
  }
}

const errors = [];

console.log(`[record] launching chromium`);
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  deviceScaleFactor: 2,
  recordVideo: {
    dir: OUT_DIR,
    size: { width: 1280, height: 720 },
  },
});

const page = await context.newPage();

page.on('console', msg => {
  if (msg.type() === 'error') errors.push(`[console.error] ${msg.text()}`);
});
page.on('pageerror', err => {
  errors.push(`[pageerror] ${err.message}\n${err.stack ?? ''}`);
});
page.on('requestfailed', req => {
  errors.push(`[requestfailed] ${req.url()} — ${req.failure()?.errorText}`);
});

const fileUrl = 'file://' + HTML_PATH;
console.log(`[record] loading ${fileUrl}`);
const navStart = Date.now();
await page.goto(fileUrl, { waitUntil: 'load' });

// Sequentially take snapshots at the planned offsets. If animation finishes
// early, remaining snapshots capture the end-state (still useful to Critic).
let elapsed = 0;
let earlyDone = false;
for (let i = 0; i < SNAP_OFFSETS_MS.length; i++) {
  const wait = Math.max(0, SNAP_OFFSETS_MS[i] - elapsed);
  await page.waitForTimeout(wait);
  elapsed = SNAP_OFFSETS_MS[i];

  let isDone = false;
  try {
    isDone = await page.evaluate(() => window.__animationDone__ === true);
  } catch { /* page might have closed */ }

  try {
    await page.screenshot({
      path: path.join(OUT_DIR, `frame_${i}.png`),
      type: 'png',
    });
    console.log(`[record] frame_${i}.png at ${elapsed}ms${isDone ? ' (animation done)' : ''}`);
  } catch (e) {
    console.log(`[record] frame_${i} screenshot failed: ${e.message}`);
    break;
  }

  if (isDone) {
    earlyDone = true;
    break;
  }
}

// If animation didn't finish during the snapshot window, keep waiting.
let timedOut = false;
if (!earlyDone) {
  try {
    await page.waitForFunction(
      () => window.__animationDone__ === true,
      null,
      { timeout: MAX_WAIT_MS - elapsed },
    );
    console.log(`[record] animation reported __animationDone__`);
  } catch {
    timedOut = true;
    errors.push(
      `[timeout] window.__animationDone__ never became true within ${MAX_WAIT_MS}ms`,
    );
  }
}

await page.waitForTimeout(TAIL_BUFFER_MS);
await context.close();
await browser.close();

// Rename auto-named webm → video.webm
const webms = fs
  .readdirSync(OUT_DIR)
  .filter(f => f.endsWith('.webm') && f !== 'video.webm');
if (webms.length > 0) {
  const newest = webms
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtime.getTime() }))
    .sort((a, b) => b.t - a.t)[0].f;
  fs.renameSync(path.join(OUT_DIR, newest), path.join(OUT_DIR, 'video.webm'));
}

if (errors.length > 0) {
  fs.writeFileSync(
    path.join(OUT_DIR, 'console_errors.json'),
    JSON.stringify(errors, null, 2),
  );
  console.log(`[record] ${errors.length} errors → console_errors.json`);
}

const videoPath = path.join(OUT_DIR, 'video.webm');
if (fs.existsSync(videoPath)) {
  const sizeKB = (fs.statSync(videoPath).size / 1024).toFixed(0);
  console.log(`[record] saved → ${videoPath} (${sizeKB} KB)`);
}

const frameCount = fs.readdirSync(OUT_DIR).filter(f => f.match(/^frame_\d+\.png$/)).length;
console.log(`[record] frames captured: ${frameCount}`);

if (timedOut) process.exit(1);
process.exit(0);
