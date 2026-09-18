# Changelog

All notable changes are documented here. The project uses semantic versioning after the first tagged release.

## 0.1.0 — 2026-09-18

### Added

- First public `audio-first-video` Codex skill
- Three-context fresh-task architecture with bounded, hash-bound handoffs
- Explicit human approval gates and deterministic release validation
- Audio locking, alignment, timing, render preflight, encoded-media QA, and byte-preserving promotion
- Apache-2.0 license, bilingual README, contribution guide, security policy, and threat model
- GitHub Actions checks for script compilation, context architecture, and deterministic regressions

### Security

- Removed personal absolute paths and private brand assets from the public package
- Reject insecure, credential-bearing, and unapproved custom TTS provider hosts
- Document untrusted-input, filesystem, subprocess, credential, network, and supply-chain boundaries

### Known limitations

- Native rendering, GPU acceleration, provider calls, browsers, codecs, and model weights require environment-specific validation
- The bundled TTS implementation is DashScope-specific; provider-neutral adapters are planned
- The first release has no claimed external adoption or download history
