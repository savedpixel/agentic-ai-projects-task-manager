# Runtime filesystem contract

The browser adapter in `src/taskmanager/js/services/server-fs.js` calls a local runtime. Python and Electron implementations expose the same retained endpoints:

- project scan;
- file read/write;
- file and folder copy-verify-delete;
- automation summary/action;
- native directory selection where available;
- projects/UI runtime JSON read/write.

Paths are resolved under user-selected project roots, traversal is rejected, writes are verified, and unexpected methods/routes fail closed. The public runtime exposes no extension-manager, credential, provider, audio, shortcut, permission, or transcription API.
