# Agentic Content Pipelines

Auditable, multi-stage Codex skills for content workflows that can read files, call network services, run media tools, and produce release artifacts.

The first included skill is [`audio-first-video`](skills/audio-first-video/SKILL.md). It separates content, audio/timing, and visual/release work into fresh tasks; binds handoffs and authoritative media with SHA-256; preserves explicit human approvals; and validates encoded output before promotion.

## Why this exists

Long agent runs fail in predictable ways: old context leaks into new decisions, generated files drift from approved inputs, a successful render is mistaken for a releasable artifact, and untrusted content reaches tools with filesystem or network authority. This repository turns those boundaries into executable contracts.

## Security model

The skill processes untrusted text, JSON, paths, media metadata, and project files. It can invoke Python, Node, browsers, FFmpeg, speech services, and transcription tools. Read [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md) before using it with sensitive projects.

## Requirements

- Python 3.10 or newer
- Node.js for a selected video composition runtime
- FFmpeg and FFprobe
- Optional: DashScope for the bundled TTS adapter
- Optional: whisper.cpp or faster-whisper for alignment

The repository does not include credentials, model weights, browsers, media binaries, or a video composition framework. Pin and verify those dependencies for your environment.

## Install as a Codex skill

Copy or symlink `skills/audio-first-video` into your Codex skills directory. Then validate the skill and its context architecture:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py skills/audio-first-video
python3 skills/audio-first-video/scripts/validate_context_budget.py \
  skills/audio-first-video/context-budget.json
```

The context-budget validator intentionally fails until the repository's isolated cold-start test has passed and the evidence is recorded in `context-budget.json`.

## Development

Run the deterministic unit suite from the skill directory:

```bash
python3 -m unittest discover -s tests -v
```

Some end-to-end media checks require native browser, GPU, codec, model, or provider access and are not silently downgraded in CI.

## Project status

Pre-release. APIs and file contracts may change before `v1.0.0`. Public metrics should be read from GitHub; this repository does not claim downloads or adoption it cannot verify.

## License

Apache-2.0. See [LICENSE](LICENSE).
