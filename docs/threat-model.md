# Threat model

## Protected assets

- API keys and provider account identifiers
- private source material and media
- files outside the selected project and toolchain roots
- approved narration, audio, timing, visual review, and release artifacts
- integrity of human approvals and validation reports

## Trust boundaries

Untrusted inputs include researched pages, copied Markdown, JSON manifests, media metadata, filenames, CLI arguments, handoff files, third-party packages, model weights, binaries, and pull requests.

High-authority sinks include filesystem writes and links, provider WebSocket calls, browser launches, Python and Node subprocesses, FFmpeg/FFprobe, transcription engines, dependency installers, and release promotion.

## Principal threats

1. Prompt injection changes agent behavior through source material or project files.
2. Path traversal or symlink substitution escapes the intended project root.
3. Untrusted values alter subprocess behavior or select unintended executables.
4. Credentials leak through CSV files, environment dumps, exceptions, logs, or handoffs.
5. A configured provider host redirects narration data to an unauthorized endpoint.
6. Replaced packages, models, browsers, or media binaries compromise the supply chain.
7. A contribution weakens approval, hash, invalidation, or fail-closed rules.
8. Active HTML, SVG, or Markdown content survives into a public artifact.

## Existing controls

- fresh-task context boundaries and bounded model inputs
- SHA-256 binding for authoritative files and selected runtimes
- schema validation and deterministic stage routers
- explicit human approval gates
- downstream invalidation after authoritative input changes
- argument-array subprocess execution
- encoded-media and public-surface validation
- byte-for-byte promotion of the approved review candidate

## Known limits

The skill cannot make third-party providers, packages, binaries, browsers, or models trustworthy. Maintainers must pin, verify, and update them. Model review is advisory; deterministic checks and human approval remain authoritative.
