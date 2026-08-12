# Test suite

`npm test` runs the deploy build, JavaScript syntax checks, parser/writer contracts, Task Manager filesystem/runtime parity, automation tests, static production audit, identity/public-release audits, and source/dist browser smoke plus filesystem E2E checks.

Browser verification uses isolated Chromium by default. Required release coverage includes desktop/mobile layouts, all retained routes, queue/detail/questions/user-verification workflows, lifecycle writes, project/settings persistence, reload/reopen, service-worker offline behavior, console errors, and unexpected network requests.

`tooling/qa/public_release_audit.py` is the publication boundary check. It rejects excluded product modules, private absolute paths, legacy app identity, live runtime/operational directories, secret-like values, and missing legal/community files.
