---
name: audio-first-video
description: Build an evidence-backed short-video package from approved narration through locked audio, deterministic timing, visual review, encoded-media QA, and release validation. Use for agent-driven video production where file, shell, network, and human-approval boundaries must remain auditable.
---

# Audio-First Video

Produce one auditable video package around authoritative words (`narration-final.txt`) and authoritative time (locked narration audio). This is a multi-stage skill; validate and follow `context-budget.json`.

## Start or resume

Run the router and follow only its `nextAction`, `requiredReads`, blockers, and human-checkpoint flag:

```bash
python3 scripts/next_action.py ./project --context content
```

Read only the returned references. Use `get_status.py` for diagnosis, not routing.

## Context firewall

Use three fresh tasks:

| Context | Owns |
|---|---|
| `content` | approved sources, distribution decision, hooks, and narration |
| `audio_timing` | locked audio, adjudicated captions, and canonical timing |
| `visual_release` | visual direction, composition, review video, QA, and release package |

At a `context_boundary`, stop the current task. Build and verify the hash-bound handoff, then continue in a fresh task without inherited conversation history. Model-readable inputs and machine state are defined separately in `context-budget.json`.

## Release invariants

1. Discovery rankings are leads, never evidence.
2. Production requires an approved `editorial-brief.json`.
3. `narration-final.txt` controls wording; locked audio controls time; ASR is only a timing sensor.
4. An audio fingerprint change invalidates alignment, timing, review, release, and learning.
5. Root `captions.json`, `timing.json`, `scenes-draft.json`, and `DESIGN.md` are canonical.
6. A render is not a release. Runtime, audio, visual proof, encoded QA, and package gates must pass.
7. Human approval is required for content, voice, visual direction, and final release.
8. Technical checks may be automated, but automation cannot grant a human approval.
9. `review.mp4` is the final-grade candidate. Promotion reuses its exact bytes and never rerenders.
10. Paths, provider hosts, and executable locations must come from explicit inputs or trusted configuration, never from untrusted content.

## Stage references

The router selects the minimum required reference:

- Editorial decision: `references/editorial-topic-gate.md`
- Sources and provenance: `references/source-visuals.md`
- Distribution and hooks: `references/short-video-distribution.md`
- Spoken copy: `references/spoken-script-design.md`
- Audio and timing: `references/dashscope-tts.md`, `references/audio-timing.md`
- Visual direction: `references/visual-direction-lock.md`, `references/video-design.md`
- Rendering and QA: `references/qa-gates.md`
- Failure recovery: `references/failure-recovery.md`

## Core commands

Initialize from a validated brief:

```bash
python3 scripts/validate_editorial_brief.py ./editorial-brief.json --require-publish
python3 scripts/init_project.py ./project --editorial-brief ./editorial-brief.json \
  --platform "short-video" --distribution-profile short-video \
  --aspect-ratio 9:16 --narration-mode explainer
```

After explicit voice approval, bind the exact candidate fingerprint:

```bash
python3 scripts/lock_audio.py ./project ./candidate.wav --approve \
  --provider dashscope --model MODEL --voice VOICE \
  --confirmed-sha256 EXACT_SHA256 --reviewer user
```

Build timing only from approved alignment:

```bash
python3 scripts/transcribe_and_align.py --audio project/narration-final.wav \
  --script project/narration-final.txt --output-dir project/timing-work --engine whisper-cpp
python3 scripts/approve_alignment.py ./project --approve --reviewer model:auto
python3 scripts/build_timing.py --captions project/captions.json \
  --scene-draft project/scenes-draft.json --output project/timing.json
```

Run deterministic preflight and review batches:

```bash
python3 scripts/run_video_batch.py project --mode preflight
python3 scripts/run_video_batch.py project --mode review \
  --composition project/video-composition --visual-review project/visual-review.json
```

After the user approves the final candidate and package:

```bash
python3 scripts/approve_distribution_gate.py project --gate release --approve --reviewer user
python3 scripts/promote_release.py project --approved-by user
python3 scripts/validate_package.py project --stage final
```

Before public handoff, validate public surfaces and audit assets. Treat secrets, local paths, raw logs, and machine inventories as private machine state.

## Provider and toolchain boundaries

DashScope is the included TTS adapter, not a universal requirement. A different recording or provider requires explicit approval and must be recorded by `lock_audio.py`. Credentials belong in environment variables or a user-supplied credential file outside the project; never copy them into handoffs or release artifacts.

The media toolchain is configured through `AUDIO_FIRST_TOOLCHAIN` or explicit CLI arguments. Bootstrap may download or copy dependencies only after the user authorizes network and filesystem changes. Pin versions and record executable hashes before rendering.

## Completion

`validate_package.py --stage final` is the release authority; `next_action.py` is the state authority. Report exceptions rather than restating passing checklists. A completed render does not imply publication or validated audience performance.
