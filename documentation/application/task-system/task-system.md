# Task system

The reusable task-system contract lives under `docs/tasks/`. Plans are twelve-section folders moved through draft, pending, approved, in-progress, review, user-verification, completion, parking, archive, failure, or blocker lifecycle directories.

`plan.json` is machine state; role-owned Markdown sections hold planning, execution, review, evidence, and comments. `docs/tasks/workflow.md`, `verification.md`, `browser-verification-policy.md`, and `review.md` are authoritative. New repositories begin with empty lifecycle directories, queue, lessons, and browser-lock state.
