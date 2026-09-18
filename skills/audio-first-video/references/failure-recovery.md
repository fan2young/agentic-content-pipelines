# Failure Recovery

## Spoken script sounds like a creator imitation

Return to the fact master. Remove signature greetings, fixed CTA language, borrowed metaphors, persona claims, and repetitive verbal tics. Keep only the abstract structure: hook, promise, evidence-led beats, turn, synthesis, and optional audience action. Rewrite in the user's own channel voice.

## Spoken script is lively but less accurate than the article

Treat this as fact drift, not a tone problem. Compare every number, causal claim, quotation, and conclusion against `article.md` and `sources.md`; restore qualifications or remove the claim. Analogies may explain evidence but never replace or strengthen it.

## Draft misses the target duration

Do not solve this by enforcing a universal characters-per-minute formula. Generate a short voice candidate with the selected provider and voice, calculate the observed rate, then cut or expand argument beats. Preserve the central thesis and evidence before decorative hooks, questions, and CTA.

## DashScope rejects the API key

Read the server error before changing code. `AccessDenied: Access denied by API-Key restrictions` means the connection reached Bailian but the key's custom access scope or IP allowlist blocked it. Ask the user to allow the selected model and the actual caller IP, or temporarily use `0.0.0.0/0` and `::/0` during a controlled connectivity test. Never print, commit, or copy the key into source files.

For a Beijing workspace export, load `apiKey`, `workspaceId`, and `apiHost` from the CSV and derive `wss://{apiHost}/api-ws/v1/inference`. Do not substitute the public Singapore endpoint.

## Streamed WAV reports an impossible duration

Do not patch the duration after the fact or trust the estimated provider WAV header. Request `PCM_24000HZ_MONO_16BIT`, collect all PCM bytes, then write a mono, 16-bit, 24 kHz WAV header locally. Verify duration from the final frame count before alignment.

## Voice sounds mechanical or is unintelligible

Stop timing work. Keep the approved narration and let the user replace the voice provider or recording. Do not polish visuals against rejected audio.

## ASR produces incorrect Chinese words

Expected behavior: ASR is a timing sensor, not copy authority. Align approved narration characters to ASR anchors. Review names, numbers, English abbreviations, and low-match spans manually.

If recognition is broadly unusable, try a larger local model, supply the approved script as an initial prompt, ensure Mandarin is selected, or obtain timestamps from the voice provider.

## Audio changes after video assembly

Compare audio fingerprints. If different, invalidate raw alignment, captions, scene timing, animation schedules, review render, and final render. Preserve article, sources, design decisions, and reusable visual assets.

Run `scripts/lock_audio.py --replace --approve` for the approved replacement. It records the new fingerprint and invokes the same deterministic invalidation map used by `scripts/invalidate_downstream.py`.

## Xcode or local transcription cannot run

Check the local toolchain and licenses. If local ASR remains unavailable, use provider timestamps or another authorized transcription path. Do not invent timestamps from text length and present them as final.

If whisper.cpp loads the Metal backend and then exits only inside the Codex sandbox, repeat the same transcription in a native local execution. `--engine whisper-cpp` is strict; `--engine auto` may fall back to faster-whisper CPU but must record the fallback reason in the alignment report.

## Guizang branch changes or fails

Record the branch as `pending` or `failed`; continue alignment and video work if they do not require its assets. Regenerate only that branch after its skill is updated.

## Timing builder chooses poor scene cuts

Edit `timing.json` or refine `scenes-draft.json`, then revalidate. Preserve continuous ranges and relative animation timing. Editorial judgment overrides equal-duration heuristics.

## Full render fails late

Re-run structural checks, render one representative frame near the failure, verify asset availability, fonts, browser support, and memory usage. Use a short review segment before repeating the full render.

## FFmpeg exists but video encoding fails

Treat “encoder listed” and “encoder usable” as different states. Run `preflight_render_runtime.py` with the exact FFmpeg path intended for HyperFrames. `libx264` may be absent; VideoToolbox may be listed yet unable to create a compression session in the current execution environment.

Do not switch to another FFmpeg implicitly. Select an explicit alternative, rerun the H.264/AAC smoke encode, record its absolute path and SHA-256 in `runtime-preflight.json`, export the same path through `HYPERFRAMES_FFMPEG_PATH` and `HYPERFRAMES_FFPROBE_PATH`, then retry only the short proof before a full render.

The fixed toolchain's public `bin/ffmpeg` and `bin/ffprobe` launchers must point to the render pair that passed the delivery-shaped smoke encode. A copied provenance binary may remain under `media/bin`, but it must not remain the public launcher when its only H.264 encoder is an unusable VideoToolbox implementation. Environment-configured render paths are preferences, not hard user pins; `preflight_render_runtime.py` may fall back to an installed `libx264` pair unless the caller explicitly passes `--ffmpeg`.

If VideoToolbox returns `-12903` only inside the Codex sandbox, do not classify the Mac as incapable. Repeat the delivery-shaped preflight in a native local execution with `--prefer-hardware`. A successful native preflight authorizes `render_local_accelerated.py --require-hardware-encode`; a sandbox preflight never authorizes hardware rendering merely because the encoder appears in inventory.
