# Security Policy

## Supported versions

Until the first stable release, only the latest commit on the default branch receives security fixes.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose credentials, overwrite files outside a project, execute unintended commands, contact an attacker-controlled host, or bypass a human approval or release-integrity gate. Use GitHub private vulnerability reporting once the repository is published.

Include the affected commit, entry point, expected boundary, minimal reproduction, and whether secrets or external systems were touched. Do not include real credentials or private media.

## Security boundaries

- Treat source text, Markdown, JSON, media metadata, filenames, handoffs, and contributed fixtures as untrusted.
- Credentials must remain outside project and release artifacts.
- Commands use argument arrays; shell interpolation is not an accepted extension mechanism.
- File operations must remain inside an explicitly selected project or toolchain root.
- Network providers and executable paths require explicit configuration.
- Automated checks cannot replace content, voice, visual-direction, or final-release approval.

See [docs/threat-model.md](docs/threat-model.md) for the maintained attack-surface inventory.
