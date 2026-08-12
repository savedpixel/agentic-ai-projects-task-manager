import assert from 'node:assert/strict';
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { createRuntimeServer } = require('../../electron/runtime-server.cjs');

const shippedJs = ['js/services/server-fs.js', ...readdirSync('dist/js', { recursive: true }).filter((name) => String(name).endsWith('.js')).map((name) => `js/${name}`).sort().filter((name, index, list) => list.indexOf(name) === index)];

assert.ok(shippedJs.includes('js/services/server-fs.js'), 'server filesystem client is shipped');
assert.ok(!shippedJs.some((name) => name.endsWith('/filesystem.js') || name === 'filesystem.js'), 'browser filesystem helper is not shipped');
assert.ok(!shippedJs.some((name) => name.endsWith('/idb.js') || name === 'idb.js'), 'IndexedDB persistence helper is not shipped');

const forbidden = /\b(indexedDB|showDirectoryPicker|FileSystemDirectoryHandle|localStorage|sessionStorage)\b/;
for (const file of shippedJs) {
  if (file.endsWith('/browser-cleanup.js')) continue;
  const text = readFileSync(join('dist', file), 'utf8');
  assert.doesNotMatch(text, forbidden, `${file} must not use browser-backed storage or filesystem APIs`);
}

const temp = mkdtempSync(join(tmpdir(), 'taskmanager-folder-copy-'));
let runtime;
try {
  const projectRoot = join(temp, 'project');
  const source = join(projectRoot, 'documentation/task/planning/pending/00001-folder');
  mkdirSync(source, { recursive: true });
  writeFileSync(join(source, 'plan.json'), JSON.stringify({ status: 'Pending', lifecycle: 'pending', sections: [] }, null, 2) + '\n');
  writeFileSync(join(source, '01-original-scope.md'), '# Scope\n');
  runtime = await createRuntimeServer({ staticDir: 'dist', runtimeDir: join(temp, 'runtime'), port: 0 }).listen();
  const response = await fetch(`${runtime.url}api/folders/copy-verify-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project: { rootLabel: projectRoot },
      taskRootPath: 'documentation/task',
      sourcePath: 'documentation/task/planning/pending/00001-folder',
      destinationPath: 'documentation/task/planning/approved/00001-folder',
      updates: {
        'plan.json': JSON.stringify({ status: 'Approved', lifecycle: 'approved', sections: [] }, null, 2) + '\n',
      },
    }),
  });
  const payload = await response.json();
  assert.equal(response.status, 200, payload.error || 'folder copy endpoint should succeed');
  assert.equal(payload.ok, true);
  assert.ok(!existsSync(source), 'source folder is deleted after verified copy');
  assert.ok(existsSync(join(projectRoot, 'documentation/task/planning/approved/00001-folder/plan.json')), 'destination manifest exists');
  assert.match(readFileSync(join(projectRoot, 'documentation/task/planning/approved/00001-folder/plan.json'), 'utf8'), /Approved/);

  const automationResponse = await fetch(`${runtime.url}api/automation/summary`);
  const automationPayload = await automationResponse.json();
  assert.equal(automationResponse.status, 200, automationPayload.error || 'automation summary should succeed');
  assert.equal(automationPayload.ok, true, 'automation summary should not fail because of runtime root resolution');
  assert.notEqual(automationPayload.error, 'ROOT is not defined', 'automation summary must not reference an undefined ROOT constant');
} finally {
  if (runtime?.server) await new Promise((resolve) => runtime.server.close(resolve));
  rmSync(temp, { recursive: true, force: true });
}

console.log('filesystem.test.mjs: pass');
