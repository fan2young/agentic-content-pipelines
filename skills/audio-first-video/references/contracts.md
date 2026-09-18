# Artifact Contracts

Use UTF-8 and project-relative paths. Keep generated timing data independent of rendering implementation.

## Required project files

```text
project/
├── manifest.json
├── sources.md
├── source-visuals.json
├── article.md
├── narration-final.txt
├── narration-final.wav | narration-final.mp3
├── scenes-draft.json
├── captions.json
├── timing.json
├── DESIGN.md
├── delivery-audio-preflight.json
├── runtime-preflight.json
├── visual-proof-report.json
├── distribution-brief.json  # Douyin / Video Account
├── hook-package.json        # Douyin / Video Account
├── first-five-proof.json    # Douyin / Video Account
├── timing-work/
│   ├── raw-asr.json
│   ├── alignment-report.json
│   └── alignment-adjudication.json
├── review.mp4              # final-grade release candidate
├── review-report.json
├── final-report.json
├── short-video/             # platform cover, title package, copy, release map, performance learning
├── asset-inventory.json     # used/unused attachment assets before public handoff
└── final.mp4
```

Branch outputs such as WeChat HTML, cards, slide HTML, raw transcripts, contact sheets, and alignment reports are optional until their branch runs.

For the shared Douyin and Video Account release, initialize one project root from the approved editorial brief and fact master. Use the `short-video` distribution profile with both distribution targets. `distribution-brief.json`, `hook-package.json`, and `first-five-proof.json` become required gates; `short-video/release-package.json` binds one shared cover and publishing surface to the byte-identical final video. Do not create platform-specific narration, timing, render, cover, copy, topic, or comment duplicates by default.

Keep root-level `captions.json`, `timing.json`, `scenes-draft.json`, and `DESIGN.md` canonical. Video-engine adapters may generate derived data during the build, but they must not create independently edited copies.

`review.mp4` is a final-grade release candidate, not a disposable low-quality preview. After user approval, `final.mp4` must be promoted byte-for-byte from it. The schema-version-2 short-video release package must carry one recommended distribution title plus 2–4 alternatives, and the final handoff must show them to the user.

The video-final approval does not authorize WeChat production. After promotion, ask for one explicit branch-start decision covering the article edit, article-title options, 2.35:1 cover, and inline images. On approval, reopen the manifest branch with `activate_wechat_branch.py`; after delivery, mark the same main-manifest stage `ready`.

`runtime-preflight.json` records the exact FFmpeg and FFprobe paths, hashes, selected H.264 encoder, delivery dimensions, pixel format, AAC mapping, and the result of a real smoke encode. Renderer configuration must consume the same paths; binary discovery alone is not sufficient.

## Writing-stage files

Keep these before narration approval:

- `article.md`: the fact master; preserve attribution, uncertainty, and analytical boundaries.
- `source-visuals.json`: the shared cross-channel ledger for source imagery, rights basis, local asset, attribution, crop, and usage decision.
- `narration-draft.txt`: an original spoken adaptation of the fact master.
- `scenes-draft.json`: editorial beats and visual intent without final timestamps.

Promote the approved spoken copy to `narration-final.txt`. Do not overwrite the fact master with the conversational adaptation.

## manifest.json

Start from `assets/manifest.template.json` with `schemaVersion: 2`. Validate it against `schemas/manifest.schema.json`. Keep each stage status one of `pending`, `ready`, `approved`, `invalidated`, `failed`, or `skipped`.

The audio fingerprint is the cache-invalidation key. If it changes, mark `alignment`, `timing`, `video_review`, and `video_final` as `invalidated`.

Use `scripts/invalidate_downstream.py` instead of updating downstream statuses by memory. Approval of corrected captions creates `timing-work/alignment-adjudication.json`; the manifest stores the approved caption SHA-256.

## captions.json

```json
{
  "version": 1,
  "audio": "narration-final.wav",
  "duration": 90.25,
  "captions": [
    {"id": "c001", "start": 0.12, "end": 2.8, "text": "这里是经过校正的旁白原文。"}
  ]
}
```

Times are seconds. Captions must be ordered, non-overlapping, non-empty, and inside the audio duration. Text must come from `narration-final.txt`, not raw ASR output.

## scenes-draft.json

Prefer a portable editorial outline:

```json
{
  "scenes": [
    {"id": "s01", "beat": "开场矛盾", "visualIntent": "冲突式大标题与价格走势"},
    {"id": "s02", "beat": "解释核心原因", "startPhrase": "真正改变市场判断的是", "visualIntent": "拆解三个驱动因素"}
  ]
}
```

Do not include final timestamps here. For every scene after the first, copy a short, unique phrase from the approved narration into `startPhrase`. After alignment, `build_timing.py` maps that phrase to the corrected caption boundary. It falls back to a pause heuristic only when an anchor is missing or ambiguous, and reports that exception for review.

## timing.json

```json
{
  "version": 1,
  "audio": "narration-final.wav",
  "audioDuration": 90.25,
  "compositionDuration": 90.75,
  "tailPad": 0.5,
  "sceneTransitions": [12.4],
  "sceneRanges": [
    {"scene": "s01", "start": 0.0, "end": 12.4, "beat": "开场矛盾"},
    {"scene": "s02", "start": 12.4, "end": 90.75, "beat": "解释核心原因"}
  ]
}
```

Scene ranges must be continuous. The first starts at zero and the last ends at `compositionDuration`. Internal animations use `currentTime - scene.start`.

## Reports and adapters

Validate canonical JSON against the matching file in `schemas/`. Both encoded-media reports use `containerDurationSeconds`; do not introduce an alternate duration field.

`visual-proof-report.json` is the pre-full-render decision record. It does not replace the later scene-by-scene encoded review.

Each file in `adapters/` declares a branch's required inputs, outputs, status stage, timing dependency, and invalidation triggers. An adapter may derive renderer-specific files, but those files never become a second content or timing authority.

When the user ends a project, record closeout in `manifest.json`. Optional branches that the user explicitly chose not to run become `skipped`; never relabel `failed` or `invalidated` work as skipped.
