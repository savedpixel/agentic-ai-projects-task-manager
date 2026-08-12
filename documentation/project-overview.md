# Project overview

Agentic AI Projects Task Manager is a local-first interface over filesystem-backed software-task records. It renders task queues, plan details, decisions, verification, activity, agents, lessons, observations, projects, and settings without requiring a hosted service.

The source of truth remains each connected project’s `docs/tasks` tree. The application parses Markdown and JSON, performs confined writes through a local Python or Electron runtime, and rescans the filesystem after mutations.

The public product starts with an empty registry in its own Application Support directory. It does not import or merge another application’s registry. No telemetry, hosted synchronization, model provider, microphone, recording, transcription, credential-store, or manager-extension capability is included.
