# Documentation index

| Keywords | Primary document | Source paths |
| --- | --- | --- |
| overview, product, privacy, local-first | `project-overview.md` | `README.md`, `src/taskmanager/` |
| architecture, folders, ownership, production boundary | `application/architecture/project-structure.md` | `src/taskmanager/`, `electron/`, `tooling/` |
| routes, shell, navigation, PWA | `application/architecture/app-shell.md` | `src/taskmanager/js/app/`, `src/taskmanager/js/ui/`, `src/taskmanager/sw.js` |
| filesystem, runtime, API, Electron, Python | `application/project-management/server-fs.md` | `src/taskmanager/js/services/server-fs.js`, `tooling/scripts/serve-runtime.py`, `electron/runtime-server.cjs` |
| registry, config, identity, projects, UI state | `application/state-management/runtime-config.md` | `src/taskmanager/js/state/runtime-config.js`, `electron/registry-resolver.cjs`, `tooling/scripts/taskmanager_registry.py` |
| build, deploy, package, desktop | `application/build-deployment/build-pipeline.md` | `package.json`, `tooling/scripts/build-deploy.py`, `tooling/actions/build_and_run.sh` |
| tests, browser, verification, release audit | `application/qa/test-suite.md` | `tooling/qa/`, `docs/tasks/verification.md` |
| task lifecycle, planning, review, user verification | `application/task-system/task-system.md` | `docs/tasks/`, `.agents/skills/` |

Update this table when a durable document or owned source route moves.
