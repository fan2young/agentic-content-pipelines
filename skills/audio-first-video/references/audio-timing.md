# Audio Lock and Timing

## Handoff requirements

Prefer lossless WAV at the provider's native sample rate, mono or stereo. Use 48 kHz when available, but retain native 24 kHz PCM from speech models rather than upsampling it. Accept high-quality MP3 when that is the user's source; never repeatedly transcode a lossy file. Preserve the original and derive working media beside it.

Before locking, confirm:

- The audio contains the exact approved narration in the intended order.
- There are no duplicated phrases, missing endings, long accidental silences, or truncated breaths.
- Tempo, pronunciation, and delivery are accepted by the user.
- The file's duration, codec, sample rate, channels, loudness, peak, and SHA-256 fingerprint are recorded.
- The confirmation names the provider, model, voice, duration, and SHA-256 of the exact candidate the user heard.
- A streamed WAV has a correct final frame count and duration. When a provider returns an estimated WAV header, request raw PCM and write the final WAV header locally.

Use `scripts/lock_audio.py` after approval and pass the exact heard candidate with `--confirmed-sha256`. DashScope is the default. A non-DashScope provider requires `--nonstandard-provider-approved-by`; replacement audio whose duration changes by more than 10% requires `--duration-change-approved-by`. The script preserves the approved bytes, records metadata, and invalidates dependent stages when the SHA changes.

When Codex generates speech, produce one recommended candidate by default. Additional voice candidates require an explicit user request or rejection of the recommendation; speculative comparison batches waste review time and context.

## Authority model

- `narration-final.txt` answers: what should the audience read?
- The locked audio answers: when should the audience see it?
- Raw ASR answers only: where are likely speech anchors?

When ASR and approved text disagree, retain approved text and align it to nearby reliable anchors. Flag low-match regions for review.

On the production Apple Silicon Mac, prefer the pinned whisper.cpp Metal model in a native local execution. The adapter must discard punctuation-only tokens, repair invalid token spans between adjacent reliable anchors, and record its engine, elapsed time, match ratio, low-confidence anchors, and caption-duration exceptions. Keep faster-whisper CPU as the deterministic fallback; never treat a hardware backend name alone as proof of a better alignment.

## Caption segmentation

Split primarily on semantic punctuation. Prefer one idea per caption. For vertical video, begin with approximately 8–16 Chinese characters per caption, then adjust for reading speed and layout.

Avoid captions shorter than about 0.45 seconds or longer than about 4.5 seconds unless the delivery requires it. Do not allow overlaps. Small silent gaps are acceptable.

## Scene segmentation

Choose scene cuts from semantic completion plus audible pauses. Avoid changing scenes in the middle of a proper noun, number, comparison, or causal phrase. Do not force equal-length scenes.

The included timing builder ranks caption boundaries by pause length and distance from an even pacing target. Treat its result as a draft requiring editorial review.

## Tail padding

Default to 0.5 seconds after audio end for a clean visual finish. Change it only deliberately. Do not stretch audio to fill a longer composition.

## Delivery-path preflight

Measure the locked source, then encode it through the same codec, sample rate, and channel count intended for the final video with `scripts/preflight_delivery_audio.py`. A mono source mapped to stereo can produce a materially different loudness result depending on the mapping. Fix the render audio path before the full video render; do not compensate by guessing at a final gain value after the fact.
