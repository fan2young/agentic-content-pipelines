# DashScope Narration Generation

Use this path when the user wants Codex to generate Chinese narration through Alibaba Cloud Bailian/DashScope.

## Credential and region contract

Accept either environment variables or the two-column API-key CSV exported by Bailian. The CSV uses the labels `apiKey`, `apiHost`, and `workspaceId`.

- Never echo the API key or place it in source code, `.env.example`, logs, or a committed file.
- Prefer reading the exported CSV directly with `--credentials-csv`.
- For a Beijing workspace, derive `wss://{apiHost}/api-ws/v1/inference` from the export and pass its workspace ID.
- Keep `.venv/`, `.env`, `.env.*`, and Python caches ignored in a project repository.

## Reproducible setup

For one-off work, create a project-local environment. On the fixed production Mac, prefer the shared toolchain Python and `requirements-runtime.txt` so TTS and alignment use one pinned environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r <skill-dir>/requirements-runtime.txt
```

Record the installed SDK version, model, voice, request ID, audio format, and first-packet delay in the project manifest or notes.

## Generate the recommended candidate

Default tested configuration for Mandarin finance narration:

- Model: `qwen-audio-3.0-tts-flash`
- Voice: `longanhuan_v3.6`
- Transport: the Beijing workspace WebSocket endpoint
- Provider output: 24 kHz, mono, 16-bit PCM
- Final candidate: PCM wrapped locally as WAV

```bash
.venv/bin/python <skill-dir>/scripts/synthesize_dashscope.py \
  --credentials-csv /absolute/path/to/workspace-apiKey.csv \
  --input narration-final.txt \
  --output narration-candidate-qwen.wav
```

Use a short sentence for the first connectivity test. After it succeeds, synthesize the complete approved script without silently rewriting it. Keep provider candidates separate from any existing narration audio.

Generate only this recommended full-length candidate by default. Do not synthesize a voice matrix or alternate model batch unless the user explicitly requests comparison or rejects the first recommendation.

## Required checks before approval

Verify the resulting WAV reports:

- mono;
- 16-bit sample width;
- 24,000 Hz sample rate;
- a plausible duration calculated from frame count;
- no truncation, duplicated phrases, or long accidental silence.

Present one playable candidate together with provider, model, voice, exact duration, and SHA-256. Have the user listen for names, numbers, English abbreviations, tone, pace, and emphasis. Lock only those exact bytes by passing the displayed SHA through `--confirmed-sha256`. If a replacement differs from the prior lock by more than 10% in duration, show both durations and obtain explicit approval before passing `--duration-change-approved-by`.

## Known failure signals

- `AccessDenied ... API-Key restrictions`: fix API-key model scope or IP allowlist; do not rewrite the client.
- `Model.AccessDenied`: grant the workspace access to the selected model or use an authorized default-workspace key.
- WebSocket connection closes immediately after task start: inspect the task-failed response stored by the SDK; surface its error code and message.
- WAV duration is implausibly large: the streamed WAV header is estimated; use raw PCM and write the header locally.
