'use strict';
/* Rebuild the deployed pnpm tree from a content store + manifest.
 *
 * The installer ships no symlinks (they need elevation/Developer Mode to
 * recreate on Windows). Instead stage-installer.py snapshots the
 * deployed tree into:
 *   store/            one copy per unique real file (keyed by manifest)
 *   app-manifest.json entries: dir | file (store key) | dirlink | filelink
 *
 * This script recreates app/ under the install dir: real dirs and files
 * first (files as hardlinks from store/, plain copy as fallback), then
 * links: directory links become NTFS junctions (no elevation needed),
 * file links become hardlinks. First occurrences own the ids; every
 * link target is the first occurrence's output path. Run once at
 * install time by the Inno Setup [Run] section; re-running it wipes
 * and rebuilds app/ (user data lives in %USERPROFILE%\.dsh, untouched).
 *
 * Usage: node setup-tree.cjs <install-dir>
 * Exit non-zero on any failure; no output on success beyond a summary.
 */
const fs = require('node:fs');
const path = require('node:path');

function fail(msg) {
  console.error(`setup-tree: ${msg}`);
  process.exit(1);
}

function main() {
  const installDir = process.argv[2];
  if (!installDir) fail('missing <install-dir> argument');
  const manifestPath = path.join(installDir, 'app-manifest.json');
  const storeDir = path.join(installDir, 'store');
  const appDir = path.join(installDir, 'app');
  if (!fs.existsSync(manifestPath)) fail(`manifest not found: ${manifestPath}`);
  if (!fs.existsSync(storeDir)) fail(`store not found: ${storeDir}`);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const entries = manifest.entries;
  if (!Array.isArray(entries) || entries.length === 0) fail('empty manifest');

  fs.rmSync(appDir, { recursive: true, force: true });

  // id -> output path of its first occurrence.
  const byId = new Map();
  const resolve = (rel) => path.join(appDir, ...rel.split('/').filter(Boolean));

  // Pass 1: dirs and files.
  let files = 0;
  for (const e of entries) {
    const dest = resolve(e.path);
    if (e.kind === 'dir') {
      fs.mkdirSync(dest, { recursive: true });
      byId.set(e.id, dest);
    } else if (e.kind === 'file') {
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      const src = path.join(storeDir, e.store);
      try {
        fs.linkSync(src, dest);
      } catch {
        fs.copyFileSync(src, dest);
      }
      byId.set(e.id, dest);
      files += 1;
    }
  }

  // Pass 2: links. Junction targets must be absolute; hardlink targets
  // must exist (pass 1 created them).
  let links = 0;
  for (const e of entries) {
    if (e.kind !== 'dirlink' && e.kind !== 'filelink') continue;
    const dest = resolve(e.path);
    const target = byId.get(e.target);
    if (!target) fail(`link target id not found: ${e.target} (for ${e.path})`);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (e.kind === 'dirlink') {
      fs.symlinkSync(target, dest, 'junction');
    } else {
      try {
        fs.linkSync(target, dest);
      } catch {
        fs.copyFileSync(target, dest);
      }
    }
    links += 1;
  }

  console.log(`setup-tree: rebuilt app/ (${files} files, ${links} links)`);
}

main();
