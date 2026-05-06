// Playwright recorder for the self-attention web animation PoC.
// Outputs WebM (Playwright native). Convert to MP4/GIF with ffmpeg if needed.
//
// Usage:
//   npm install
//   npx playwright install chromium
//   node record.mjs

import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, 'output');
const ANIM_DURATION_MS = 32_000; // ~30s anim + 2s tail

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

console.log('[record] launching chromium…');
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
const fileUrl = 'file://' + path.join(__dirname, 'index.html');
console.log(`[record] loading ${fileUrl}`);
await page.goto(fileUrl);

// Wait for fonts + auto-play start
await page.waitForFunction(() => typeof window.__playPoC__ === 'function');
await page.waitForTimeout(500);

console.log(`[record] capturing ${ANIM_DURATION_MS}ms…`);
await page.waitForTimeout(ANIM_DURATION_MS);

await context.close();
await browser.close();

// Rename the auto-named webm to something predictable
const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.webm'));
if (files.length > 0) {
  const latest = files
    .map(f => ({ f, t: fs.statSync(path.join(OUT_DIR, f)).mtime.getTime() }))
    .sort((a, b) => b.t - a.t)[0].f;
  const target = path.join(OUT_DIR, 'self_attention.webm');
  fs.renameSync(path.join(OUT_DIR, latest), target);
  console.log(`[record] saved → ${target}`);
  console.log('');
  console.log('Convert to MP4:');
  console.log(`  ffmpeg -i ${target} -c:v libx264 -pix_fmt yuv420p ${OUT_DIR}/self_attention.mp4`);
  console.log('Convert to GIF:');
  console.log(`  ffmpeg -i ${target} -vf "fps=15,scale=960:-1:flags=lanczos" ${OUT_DIR}/self_attention.gif`);
} else {
  console.error('[record] no webm produced');
  process.exit(1);
}
