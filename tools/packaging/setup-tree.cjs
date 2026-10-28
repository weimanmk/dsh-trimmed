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
 * install time by the Inno Setup [Code] section; re-running it wipes
 * and rebuilds app/ (user data lives in %USERPROFILE%\.dsh, untouched).
 *
 * Windows long paths: the pnpm virtual store nests node_modules chains
 * up to 825 chars, far past MAX_PATH (23k+ manifest entries exceed a
 * 260-char budget under a typical install dir). Every filesystem path
 * used here is therefore prefixed with \\?\ on Windows, which exempts
 * the whole resolution (including junction reparse) from MAX_PATH.
 * Junction TARGETS stay plain absolute paths: libuv/kernel reparse
 * handling expects the unprefixed form; only the link location itself
 * is prefixed.
 *
 * Diagnostics: failures also write <install-dir>\setup-tree-error.log
 * and %TEMP%\dsh-trimmed-setup-tree.log (the installer's console output
 * is hidden, so a bare stderr message is undiagnosable; run #12 failed
 * exactly this way). Success writes a summary line to the %TEMP% log.
 *
 * Usage: node setup-tree.cjs <install-dir>
 * Exit non-zero on any failure.
 */
const fs = require('node:fs');
const path = require('node:path');

const isWin = process.platform === 'win32';

/** Prefix an absolute path with \\?\ on Windows (identity elsewhere). */
function lp(p) {
  if (!isWin) return p;
  const abs = path.resolve(p);
  return abs.startsWith('\\\\?\\') ? abs : '\\\\?\\' + abs;
}

function logLine(msg) {
  const line = `setup-tree: ${msg}\n`;
  process.stdout.write(line);
  try {
    const tmp = process.env.TEMP || process.env.TMP;
    if (tmp) fs.appendFileSync(path.join(tmp, 'dsh-trimmed-setup-tree.log'), line);
  } catch {
    /* logging must never break the install itself */
  }
}

function fail(msg) {
  const err = new Error(msg);
  err.setupTreeFailure = true;
  throw err;
}

function main() {
  const installDir = process.argv[2];
  if (!installDir) fail('missing <install-dir> argument');
  const manifestPath = lp(path.join(installDir, 'app-manifest.json'));
  const storeDir = lp(path.join(installDir, 'store'));
  const appDir = lp(path.join(installDir, 'app'));
  if (!fs.existsSync(manifestPath)) fail(`manifest not found: ${manifestPath}`);
  if (!fs.existsSync(storeDir)) fail(`store not found: ${storeDir}`);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const entries = manifest.entries;
  if (!Array.isArray(entries) || entries.length === 0) fail('empty manifest');

  logLine(`rebuilding app/ from ${entries.length} entries under ${installDir}`);
  fs.rmSync(appDir, { recursive: true, force: true });

  // id -> plain absolute output path of its first occurrence.
  const byId = new Map();
  const resolve = (rel) => path.join(installDir, 'app', ...rel.split('/').filter(Boolean));

  // Pass 1: dirs and files.
  let files = 0;
  for (const e of entries) {
    const dest = lp(resolve(e.path));
    if (e.kind === 'dir') {
      fs.mkdirSync(dest, { recursive: true });
      byId.set(e.id, resolve(e.path));
    } else if (e.kind === 'file') {
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      const src = lp(path.join(storeDir, e.store));
      try {
        fs.linkSync(src, dest);
      } catch {
        fs.copyFileSync(src, dest);
      }
      byId.set(e.id, resolve(e.path));
      files += 1;
    }
  }

  // Pass 2: links. Junction targets must be absolute (plain form);
  // hardlink targets must exist (pass 1 created them).
  let links = 0;
  for (const e of entries) {
    if (e.kind !== 'dirlink' && e.kind !== 'filelink') continue;
    const dest = lp(resolve(e.path));
    const target = byId.get(e.target);
    if (!target) fail(`link target id not found: ${e.target} (for ${e.path})`);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (e.kind === 'dirlink') {
      fs.symlinkSync(target, dest, 'junction');
    } else {
      try {
        fs.linkSync(lp(target), dest);
      } catch {
        fs.copyFileSync(lp(target), dest);
      }
    }
    links += 1;
  }

  logLine(`rebuilt app/ (${files} files, ${links} links)`);
}

try {
  main();
} catch (err) {
  const detail = `FAILED: ${err && err.stack ? err.stack : String(err)}\n`;
  try {
    fs.writeFileSync(
      path.join(process.argv[2] || '.', 'setup-tree-error.log'),
      detail,
    );
  } catch {
    /* fall through to stderr */
  }
  try {
    const tmp = process.env.TEMP || process.env.TMP;
    if (tmp) fs.appendFileSync(path.join(tmp, 'dsh-trimmed-setup-tree.log'), detail);
  } catch {
    /* fall through to stderr */
  }
  console.error(detail);
  process.exit(1);
}
