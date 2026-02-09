#!/usr/bin/env node
/**
 * Kill processes on ports 3000/3001, remove Next.js dev lock, then start dev.
 * Run from repo root: node scripts/dev-fresh.js
 */
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const lockPath = path.join(process.cwd(), 'frontend', '.next', 'dev', 'lock');

// Kill ports (ignore errors if nothing is listening)
try {
  execSync('npx --yes kill-port 3000 3001', { stdio: 'inherit' });
} catch (_) {}
// Remove lock file
try {
  fs.unlinkSync(lockPath);
} catch (_) {}
// Start dev (replace current process so Ctrl+C works)
const isWindows = process.platform === 'win32';
spawn(isWindows ? 'npm.cmd' : 'npm', ['run', 'dev', '--prefix', 'frontend'], {
  stdio: 'inherit',
  shell: true,
  cwd: process.cwd(),
});
