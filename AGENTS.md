# TaskManager Agent Instructions

## TaskManager lifecycle coordinator subagent identity

When coordinating TaskManager lifecycle work from heartbeat automations, distinguish
Codex subagent threads from TaskManager registry agent IDs:

- A Codex subagent/thread ID is generated only by the Codex subagent tool when a
  thread is spawned. It cannot be chosen by prompt, `--agent-id`, or nickname.
- The TaskManager registry `--agent-id` is only metadata inside
  `data/runtime/automation-assignments.json` and plan stamps. It does not reuse,
  rename, or select a Codex subagent thread.
- Do not spawn a fresh Codex subagent just to reuse a deterministic registry
  `--agent-id`. Reuse/resume the existing known Codex thread for that registry
  identity whenever possible.
- For each project/build registry identity, keep at most one live Codex thread:
  `<project-slug>-build-agent`. Send additional project-agent work for that
  project to that thread with `send_input`; do not spawn another build agent.
- Reviewer threads are the only normal concurrency exception. Spawn at most one
  reviewer thread per review-ready plan, named in the registry as
  `<project-slug>-reviewer-<plan-slug>`.
- Before spawning any lifecycle subagent, first reconcile, then check known open
  Codex threads and active/stale registry leases. Spawn only when there is no
  usable known thread for that deterministic registry identity, or when resume
  has failed and the prior lease is expired/released/blocked.
- Close completed Codex subagent threads promptly after recording their result so
  the app does not accumulate old open agents.

## Repository shape

TaskManager uses a production source/data/tooling separation:

- `src/taskmanager/` is the only production web-app source tree.
- `src/taskmanager/js/app/` owns boot, routing, and route composition.
- `src/taskmanager/js/features/` owns route-level UI modules.
- `src/taskmanager/js/domain/` owns task Markdown parsing and writing.
- `src/taskmanager/js/services/` owns runtime filesystem/project orchestration.
- `src/taskmanager/js/state/` owns runtime config and app state.
- `src/taskmanager/js/ui/` owns reusable UI primitives and view helpers.
- `src/taskmanager/css/` is split by cascade layer; keep `styles.css` as the import manifest.
- `tooling/` owns scripts, QA, macOS helpers, and action launchers.
- `documentation/` owns application docs and QA evidence.
- `data/reference-mockup/` is reference-only and must never be deployed.
- `dist/` is generated output; never edit it by hand.

## Development rules

- Keep production builds free of mockup, dummy, test, or reference content.
- Update `documentation/0-index.md` when adding or moving durable docs or feature routes; this cleaned documentation structure does not use the old documentation/index file or a separate JSON search index.
- Update `src/taskmanager/sw.js` whenever adding production source assets that must work offline.
- Run `npm test` after changing source paths, build tooling, Electron runtime paths, or deploy boundaries.
- After any application source change that should be visible in the desktop app, rebuild and relaunch Electron with `tooling/actions/build_and_run.sh --verify`. Use `tooling/actions/build_and_run.sh --test --verify` when the change has not already passed `npm test`. The script builds first, then requests a graceful TaskManager quit only before replacing the installed app; if needed it may force-close only the installed TaskManager app processes, never unrelated agent processes.
- Do not commit or push without explicit user approval for that action.

## Hard Plan-Task Gate

For any non-trivial implementation, documentation-structure, workflow, generator, UI, source, configuration, runtime, automation, verification, or task-system change, the agent MUST use `.agents/skills/plan-task/SKILL.md` before editing project files. The agent MUST create or update a draft plan under `docs/tasks/planning/draft/`, present the full Plan Quality Assessment in chat, and wait for the required approval/lifecycle movement before implementation.

Small read-only inspections and direct answers may proceed without a plan. File edits may bypass this gate only when the user explicitly requests a narrow mechanical edit and explicitly says no plan is required.

<!-- documentation-system:start -->
## Documentation System

Before changing behavior, architecture, public interfaces, data, configuration, integrations, deployment, or user-facing workflows:

1. Read `documentation/AGENTS.md` first.
2. Read `documentation/0-index.md` next and search its routing matrix using task keywords.
3. Read every matched primary/supporting document and inspect its listed source paths.

After verified implementation, apply `$update-documentation` whenever the contract in `documentation/AGENTS.md` and `documentation/0-index.md` applies. This includes changes to: user-facing behavior, UI, routes, states; public APIs, events, services; data models, schemas, persistence; architecture, module boundaries, file ownership; configuration, build, deployment; and documentation structure, index routes, or keywords. Update the smallest accurate docs and every touched `documentation/0-index.md` route entry. If no durable update is needed, record the exact evidence-based reason.

For deep initial/adoption work, use `$one-shot-documentation`.

The full documentation maintenance contract now lives in `documentation/AGENTS.md` and the single routing index `documentation/0-index.md`. This cleaned documentation structure does not use the old documentation-workflow/search-index/search-keywords/index files.

Never delete existing documentation. Preserve or redirect old paths only after snapshot and validation under `data/archive/documentation-migration/`.

Documentation closeout requires both:

- `DOCUMENTATION STRUCTURE REVIEW APPROVED`
- `DOCUMENTATION ACCURACY REVIEW APPROVED`

Never auto-commit or auto-push documentation changes.
<!-- documentation-system:end -->

<!-- task-system:start -->
## Task System

Generated task-system root: `docs/tasks`.

- Task root: `docs/tasks`; authoritative workflow: `docs/tasks/workflow.md`.
- Use `.agents/skills/plan-task/SKILL.md` before non-trivial edits; approved implementation starts only from `docs/tasks/planning/approved/`.
- Use `.agents/skills/execute-plan`, `.agents/skills/review-task`, `.agents/skills/user-verification`, `.agents/skills/correct-task`, and `.agents/skills/document-task` for lifecycle work.
- New plans are folders under `docs/tasks/planning/<lifecycle>/` with `plan.json` plus the canonical section files.
- Create/update draft plan folders before presenting planning questions. Record full question text, options, recommendations, answers, and the Plan Quality Assessment in `02-planning-and-decisions.md`.
- Present planning questions and approval choices in plain chat, record answers in the plan, and do not auto-select recommended answers unless the user explicitly chooses that bundle.
- Lifecycle folders are `draft`, `pending`, `approved`, `in-progress`, `review`, `user-verification`, `failed-user-verification`, `completed`, `archive`, `parked`, and `blocker`. Only `approved/` is normally buildable.
- Technical verification policy is external. Read `docs/tasks/verification.md`, `docs/tasks/browser-verification-policy.md`, and `docs/tasks/review.md`. Task artifacts record verification requirements/status/evidence references; never duplicate browser/tool/screenshot policy.
- After independent R1 implementation approval, the executor/build agent handles the commit gate; reviewers review only the work done and must not inspect, judge, block, or comment on dirty-tree or commit-boundary state. The executor stages only task-related files, never broad `git add -A` with unrelated dirty files, never stashes without explicit user approval, asks the user if a safe task-only commit is ambiguous, then updates docs/logs/observations, checks `User Verification Required` as the final post-implementation item, and moves to `user-verification/`. Never push automatically.
- Observations live at `documentation/agent-observations/` for durable application observations and `docs/tasks/lessons*.md` for task-system lessons.
<!-- task-system:end -->

<!-- verification-system:start -->
## Verification System

Generated verification root: `docs/tasks`.

### Authoritative Entrypoints

- **Verification policy:** `docs/tasks/verification.md`
- **Browser verification policy:** `docs/tasks/browser-verification-policy.md`
- **Verification review:** `docs/tasks/review.md`
- **Atlas lock:** `docs/tasks/automation/browser-locks/atlas-browser-lock.json`
- **Browser verification skill:** `.agents/skills/browser-verification/SKILL.md`

### Default Browser Lane

Default to isolated Chromium/Playwright for browser-facing verification. Use Atlas / Computer Use only when explicitly required by the approved plan or user and only while holding the Atlas lock.

### Screenshot Storage

- Raw/testing: `data/temp/screenshots/YYYY-MM-DD-{task-slug}/`
- Curated proof: `docs/tasks/planning/<lifecycle>/<plan-folder>/evidence/proof-screenshots/`
- Keep raw screenshots out of Git; promote only curated proof images required as evidence.
<!-- verification-system:end -->

<!-- BEGIN MANAGED BLOCK: codex-task-system -->
## Codex Task System

- Runtime: Codex only.
- Task root: `docs/tasks` unless this managed block was installed with a project-specific existing task root.
- Before planning or implementation, classify the request as Quick Fix, Standard Plan, or Full Robust Plan.
- Use `.agents/skills/quick-fix/SKILL.md` for single-purpose, isolated, low-risk fixes that qualify for the fast path.
- Use `.agents/skills/plan-task/SKILL.md` for planning.
- Use `.agents/skills/execute-plan/SKILL.md` for approved implementation.
- Use `.agents/skills/review-task/SKILL.md` for R1/R2 reviews.
- Plans are folders under `docs/tasks/planning/<lifecycle>/`.
- Create new plan folders with `python3 docs/tasks/task-system-helpers/create-plan-folder.py --project-root . --title "<task title>" --codex-end-goal "<concise outcome-level goal with completion guard>"`; direct creation is only a fallback after recording the helper failure.
- Plan files are role-owned: planner files freeze after approval; executor files are for execution reports/evidence; reviewer files are for R1/R2 review; `plan.json` is TaskManager/helper-owned machine state; comments are append-only.
- Live checklist progress belongs only in implementation/testing/post-implementation checklist files; reports and evidence must use tables or normal bullets.
- Planning questions and approval choices must be presented in plain chat only; do not use interactive transport tooling for planning questions.
- Clarification questions must include the full question, why it matters, exactly three clear options, a recommended answer, all material questions that affect the task, a six-question limit when possible, and a `recommended` bundle when six or fewer questions are asked.
- Every plan must include and chat-present a Plan Quality Assessment: what is good, what is risky/not good, what was not accounted for, assumptions, recommended path, plan score, why it is not 10/10, and approval readiness. Repeat that full review in the same message before asking for approval, `move to approved`, `move to pending`, execution, parking, next steps, or lifecycle movement.

### Task-System Config

Read `docs/tasks/task-system.config.yaml` for project-local defaults. The generator creates it only when missing and must not overwrite user edits. New plans snapshot the effective settings into `plan.json.taskSystemConfigSnapshot`, so future changes affect future tasks rather than silently changing existing plans.

Config controls default planning mode, whether `$plan-task --quick` / `$plan-task --standard` / `$plan-task --full` overrides are allowed, Codex goal tool usage, whether independent R1 review is required, whether executor auto-spawns and waits for reviewer sub-agents, and whether plans left in `user-verification` count as agent-complete/done. If `lifecycle.userVerification.treatAsDoneForAgentWork` is true, agents must not call a plan dirty, stale, blocked, incomplete, or active merely because it remains in `docs/tasks/planning/user-verification`.

### Explicit Plan-Task Mode Parameters

Recognize `$plan-task --quick`, `@plan-task --quick`, `/plan-task --quick`, and `plan-task --quick` as Quick Fix Mode requests; `$plan-task --standard`, `@plan-task --standard`, `/plan-task --standard`, and `plan-task --standard` as Standard Plan Mode; and `$plan-task --full`, `@plan-task --full`, `/plan-task --full`, `plan-task --full`, or `--robust` as Full Robust Plan Mode. `--quick` cannot bypass hard exclusions; escalate when unsafe and record requested mode, effective mode, and reason.

### Quick Fix and Pre-flight Readiness

Quick Fix Mode bypasses the 12-file plan folder only for a single-purpose, isolated, low-risk fix with an obvious target, normally one to three touched files, no material compatibility/migration/security/auth/provider/data/schema/deployment risk, no broad UI or cross-module coordination, and one straightforward verification path. Quick Fix Mode must still inspect relevant docs/source, run the `Pre-flight Readiness Gate`, run targeted verification, and append `docs/tasks/quick-fixes/YYYY-MM-DD.md`.

Before editing in Quick Fix or Execute Plan mode, run a proportional `Pre-flight Readiness Gate`: identify required runtime dependencies such as database, dev server, package install, migration state, port, browser, credentials, or provider readiness; use the cheapest documented health check; record `not required` when irrelevant; and stop early instead of repairing unrelated infrastructure when a required dependency is unhealthy.

### Plan Next-Step Choices

When asking what to do next with an approval-ready plan, end with exactly: `1. Move to approved and execute the plan using the execute-plan skill. 2. Move to pending. 3. Park.` The user may reply `1`, `2`, or `3`; `1` means approve and execute with `execute-plan`, `2` means move to pending, and `3` means park with a recorded reason.

### Codex Goal Contract

Every plan must define a clear, concise `Codex End Goal` in `plan.json.codexEndGoal`, `01-original-scope.md`, the Plan Quality Assessment, and the chat review when the effective config requires it. It must describe the finished task outcome and core completion guard without repeating the implementation plan, testing checklist, documentation checklist, review process, or every detailed item in the plan. It must not be satisfiable by a minimum-only, shortcut, placeholder, or partial-delivery result. Executors must set that objective with the Codex goal feature before implementation only when `taskSystemConfigSnapshot.config.codexGoal.enabled` is true. When disabled, record the config-controlled skip and do not call goal tools. Do not set a token budget unless the user explicitly requested one. Do not mark a goal complete until the objective is actually achieved and no required work remains.
When goal setting is enabled, executors must call `get_goal` and call `create_goal` with the exact objective when no unfinished goal is active.

### Post-Plan Change Preparation

After a plan has already been executed or moved through review/user verification, additional user-requested changes must not be blindly implemented. Even when no new plan is created, first read relevant documentation, scan relevant code/source paths, understand the current implementation, ask clarification questions when needed, then make the change, rerun verification, and update documentation where needed.

### Path-Aware Lessons System

Use the 3-layer lessons system:

- `docs/tasks/lessons-active.md` — curated evergreen lessons; read first.
- `docs/tasks/lessons-index.json` — match by task keywords, expected or confirmed touched paths, and workflow type.
- `docs/tasks/lessons.md` — full archive; read only for matched lesson IDs needing extra context or when recording a new correction.

Planning must state `Relevant Lessons` with matched lesson IDs/titles, or `Relevant lessons: none.` Execution, correction, review, verification, and documentation work must state `Applied lessons` with matched lesson IDs/titles, or `Applied lessons: none.` Evergreen corrections must be added to all three layers.

### Executor Review Wait Handoff

After moving work to review and spawning an independent reviewer, the executor/build agent must immediately use the platform wait tool, preferably Codex `wait_agent`, to stay active until the reviewer returns or wait-capable tooling fails. The executor must action reviewer feedback in the same active context, rerun verification, spawn a fresh reviewer, and wait again; on approval it proceeds to the executor-owned commit and user-verification handoff. Do not leave the user to reactivate the executor after a passive reviewer handoff.

### R1 Commit Boundary

Reviewers review only the work that was done against the approved plan, required tests, evidence, and checklist state. Reviewers must not inspect, judge, approve, reject, block, or comment on repository-wide dirty-tree state, unrelated dirty files, staging safety, stash safety, commit feasibility, or whether a commit should be attempted. After R1 approval, the executor/build agent handles commit: stage only task-related files, never broad `git add -A` with unrelated dirty files, never stash without explicit user approval, and ask the user to choose when a safe task-only commit is ambiguous.

### Non-Blocking Commit Action Needed

If implementation, verification, independent R1 approval, documentation/log/observation handoff, and user-verification movement are complete, but the local commit is ambiguous or not created, do not use the big blocked banner. Start the response with `# ✅ TASK READY FOR USER VERIFICATION — COMMIT ACTION NEEDED`, state that commit is the only unresolved follow-up, and end with `## Choose one commit option` containing numbered choices: commit named task files, include all dirty files, stash unrelated then commit/restore, or waive the local commit and leave the task in user verification.

### High-Visibility Blocked Responses

If execution, review, verification, documentation handoff, lifecycle movement, or tooling is blocked, the next chat response MUST start with `# 🚨 BLOCKED — ACTION REQUIRED` as the first visible line, followed by blocked stage, plan, blocking issue, what was tried, what remains incomplete, required action, and work status. Do not bury blockers at the end of progress updates. A local commit issue after successful user-verification handoff is not a blocker; use the non-blocking commit action needed format.

### Self-Improvement Loop

After any user correction, add a reusable lesson that prevents recurrence. Re-check active/index lessons when scope changes or touched paths are not covered by the initial lookup.

- Do not push commits without explicit user approval.
<!-- END MANAGED BLOCK: codex-task-system -->
<!-- BEGIN MANAGED BLOCK: codex-documentation-system -->
## Codex Documentation System

- Runtime: Codex only.
- Documentation root: `documentation`.
- The documentation generator always runs one-shot documentation after installing/updating this system; do not ask for reconfirmation.
- Use `.agents/skills/one-shot-documentation/SKILL.md` for deep project documentation creation/adoption.
- Use `.agents/skills/update-documentation/SKILL.md` after behavior, configuration, API, workflow, verification, or documentation-routing changes.
- Active index: `documentation/0-index.md` only.
- Maintenance workflow: `documentation/AGENTS.md` and `documentation/0-index.md`.
- Validation entrypoint: `documentation/application/qa/test-suite.md` for application verification plus link/source-path checks for documentation-only changes.
- Preserve legacy docs such as `docs/` unless the user explicitly approves migration/deletion.
<!-- END MANAGED BLOCK: codex-documentation-system -->

Do not ask for reconfirmation. Generator invocation authorizes the package install/update and one-shot documentation run.

<!-- BEGIN MANAGED BLOCK: agent-browser-verification -->
## Agent Browser Verification

- Default to isolated Chromium / Playwright.
- Prefer Chrome for Testing; system Chromium is last resort and must use `--disable-features=MacAppCodeSignClone`.
- Use bounded timeouts and `try/finally`; close every browser/page/tab/window created by the task.
- Use `scripts/mcp-browser-clean/mcp-chromium-agent-wrapper.sh --agent-id "$AGENT_ID"` for Chromium MCP.
- Use Atlas / Computer Use only when explicitly required.
- Acquire `docs/tasks/automation/browser-locks/atlas-browser-lock.json` before touching `com.openai.atlas`.
- Preserve pre-existing Atlas tabs, close every task-created Atlas tab/window, then release the lock.
- Store proof screenshots under `docs/tasks/planning/<lifecycle>/<plan-folder>/evidence/proof-screenshots/`.
<!-- END MANAGED BLOCK: agent-browser-verification -->
