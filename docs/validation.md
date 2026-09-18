# Validation evidence

## 2026-09-18 public-repository cold start

The repository was copied to a new temporary directory without `.git` metadata. The isolated copy received no conversation history and did not read sibling projects.

Checks performed:

- skill structure validation
- multi-stage context-budget validation
- compilation of every Python script
- deterministic unit and security suite: 9 tests passed
- scan for personal absolute paths, removed brand identifiers, private keys, and common API-token patterns

The cold-start result does not claim that provider calls, native browser/GPU rendering, codecs, or downloaded model weights work on every machine. Those remain explicit environment-dependent preflight gates.

Release evidence must be regenerated if a change affects the skill entrypoint, context architecture, stage router, handoff, approval, path, provider, subprocess, validation, or release-authority code.
