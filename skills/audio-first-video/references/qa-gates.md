# QA Gates

## Gate 1: Content and audio lock

- Sources support time-sensitive factual claims.
- The article or research memo is the fact master; the spoken script does not introduce unsupported facts or stronger causality.
- The opening earns attention without clickbait, creator impersonation, or a promise the body does not fulfill.
- Questions, analogies, second-person address, sponsor copy, and CTA each serve a clear function; remove them when they do not.
- For Douyin and Video Account, `distribution-brief.json` and the selected `hook-package.json` are approved; the spoken hook identifies the subject by two seconds, fulfills a bounded payoff or promise by five seconds, and declares one primary audience action or an explicit reason for none.
- Names, numbers, abbreviations, units, and pronunciation-sensitive phrases have been checked for speech.
- The user approved `narration-final.txt`.
- Locked audio matches the approved narration.
- Audio fingerprint and technical metadata are recorded.
- The real delivery codec and channel mapping pass `preflight_delivery_audio.py`.

## Gate 2: Alignment and timing

- Alignment coverage is reviewed; investigate any low-confidence region.
- `timing-work/alignment-adjudication.json` records explicit approval and the canonical caption fingerprint.
- Captions preserve approved wording.
- Caption timestamps are monotonic, non-overlapping, and in bounds.
- Scene cuts follow semantic beats or pauses.
- Timing contains no unexplained dead zone.

## Gate 3: Composition preflight

- `runtime-preflight.json` passes a real H.264/AAC MP4 encode at the delivery dimensions and frame rate using the exact FFmpeg/FFprobe paths exported to HyperFrames.
- A hardware-accelerated render uses a native local execution, records `h264_videotoolbox` in `runtime-preflight.json`, and is launched through `render_local_accelerated.py`; its render report records browser GPU mode, encoder, elapsed time, and output fingerprint.
- `video-design-report.json` passes the Next Variable video design contract.
- `source-visuals.json` passes with decided usage, local media, attribution, rights notes, and crop context.
- `visual-proof-report.json` approves light, dark, and composite representative states plus a 10–30 second motion proof before any full render.
- A short-video `first-five-proof.json` separately approves sampled frames at 0, 0.5, 1, 2, 3, and 5 seconds plus a 5–8 second proof clip before the general motion proof.
- A persistent Next Variable marker is legible in the safe area and the brand is identifiable at the opening, midpoint, and close.
- The primary and secondary visual engines differ from the repeated shell used in recent episodes; the latest-three-episode audit is recorded when those episodes exist.
- No more than two consecutive beats rely only on type/data, and each factual section has traceable evidence or a mechanism visual.
- Every logical scene has a meaningful mid-scene state change; long scenes do not become static after entrance animations.
- Treat `video-design-report.json` as structural evidence only. The visual reviewer must independently reject repeated cards, identical shells, slide-like cuts, token visual-engine changes, and brand markers absent from sampled encoded frames.
- HyperFrames structural checks pass without errors.
- Text remains within safe areas and has adequate final-pixel contrast, including semi-transparent panels over real imagery.
- Data, labels, and sources are readable on a phone-sized viewport.
- Audio, captions, and scene state all use the same timing source.
- No asset depends on an unavailable local-only URL at render time.
- Every connector has a declared semantic: arrows mean sequence or causality; branches require mutually exclusive or explicitly additive outcomes; independent conditions use aligned rows, not a fork. Reject a visually neat diagram when the relationship is false.
- Reader-facing frames contain no production language such as “原创机制图”, “设计思路”, “安全区”, connector geometry notes, or asset-strategy explanations.

## Gate 4: Visual sampling

Inspect at least one representative frame from every scene and a midpoint frame from every transition. Check the first frame, final spoken frame, and final composition frame separately.

Reject black frames, stale captions, incomplete wipes, unintentional overlaps, broken glyphs, clipping, visually empty intervals, repeated card walls, slide-like shell repetition, and brand markers that disappear or compete with captions.

Also reject semantically misleading connectors and any internal production annotation visible in the encoded frame. Pixel alignment does not rescue a false relationship.

When local Muse Glimmer is available, a manifest-driven sidecar may check the already sampled frames one question at a time: overlap, safe-area readability, locked-caption fidelity, and expected visual state. Keep full reports in machine state and surface exceptions only. This sidecar never approves aesthetics, replaces scene/transition coverage, opens the video directly, edits files, or changes encoded-QA authority.

For Douyin and Video Account, inspect the encoded first frame and 2-second and 5-second states against the approved hook. Reject a slow brand intro, an abstract editorial-slide opening, tiny competing copy, a hidden subject, a late payoff, or fewer than two meaningful state changes by five seconds.

## Gate 5: Release candidate and promotion

Render `review.mp4` once using the final delivery dimensions, frame rate, encoding quality, duration, and loudness. Treat it as the release candidate. Run the complete encoded-media QA on this file and return a compact structured summary; keep progress logs and normal diagnostics out of model context.

Use `scripts/qa_encoded_media.py` for deterministic container, stream, duration, loudness, true-peak, fingerprint, and black-interval checks. Automatic checks do not replace visual review: provide a separate visual-review record covering every scene and transition.

After explicit user approval, promote the exact candidate bytes to `final.mp4` without rerendering. Record:

- dimensions, frame rate, video codec, audio codec;
- audio and composition durations;
- integrated loudness and true/sample peak when available;
- file size and SHA-256 fingerprint.

Suggested delivery target for spoken social video: roughly -16 to -19 LUFS integrated, with no clipping. Treat platform requirements and the user's preference as authoritative.

The final gate passes only when `review.mp4` and `final.mp4` have the same SHA-256 fingerprint, final package validation passes, and `manifest.json` plus `final-report.json` record the approved artifact.

For the shared Douyin and Video Account release, the final gate also requires one approved cover, publish copy, topic set, pinned comment, release-package mapping, shared-safe-area approval, and one primary audience action. Public surfaces must use platform-neutral wording. Publication does not complete the learning loop: validate platform-tagged 24/72-hour snapshots afterward and carry the single-variable decision into the next episode.
