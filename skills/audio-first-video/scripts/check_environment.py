#!/usr/bin/env python3
"""Check the shared audio-first production runtime without exposing credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


DEFAULT_ROOT = Path.home() / ".local/share/audio-first-video/toolchain"


def execute(command: list[str], env: dict[str, str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, env=env, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    output = (result.stdout.strip() or result.stderr.strip()).splitlines()
    return result.returncode == 0, output[0] if output else f"exit {result.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain", type=Path, default=Path(os.environ.get("AUDIO_FIRST_TOOLCHAIN", DEFAULT_ROOT)))
    parser.add_argument("--deep", action="store_true", help="also load the Whisper model fully offline")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.toolchain.resolve()
    bin_dir = root / "bin"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str, required: bool = True) -> None:
        checks.append({"name": name, "passed": passed, "required": required, "detail": detail})

    inventory = root / "toolchain.json"
    add("inventory", inventory.is_file(), str(inventory))
    for name in ("ffmpeg", "ffprobe", "node", "hyperframes", "python"):
        path = bin_dir / name
        add(f"binary:{name}", path.exists() and os.access(path, os.X_OK), str(path))
    for name, flag in (("ffmpeg", "-version"), ("ffprobe", "-version"), ("node", "--version"), ("hyperframes", "--version"), ("python", "--version")):
        ok, detail = execute([str(bin_dir / name), flag], env)
        add(f"run:{name}", ok, detail)

    render_ffmpeg = Path(env.get("AUDIO_FIRST_RENDER_FFMPEG", env.get("HYPERFRAMES_FFMPEG_PATH", bin_dir / "ffmpeg"))).resolve()
    render_ffprobe = Path(env.get("AUDIO_FIRST_RENDER_FFPROBE", env.get("HYPERFRAMES_FFPROBE_PATH", render_ffmpeg.with_name("ffprobe")))).resolve()
    add("render-binary:ffmpeg", render_ffmpeg.is_file() and os.access(render_ffmpeg, os.X_OK), str(render_ffmpeg))
    add("render-binary:ffprobe", render_ffprobe.is_file() and os.access(render_ffprobe, os.X_OK), str(render_ffprobe))
    encoder = ""
    if render_ffmpeg.is_file() and render_ffprobe.is_file():
        encoder_query = subprocess.run([str(render_ffmpeg), "-hide_banner", "-encoders"], text=True, capture_output=True, env=env, timeout=10)
        encoder_text = encoder_query.stdout + encoder_query.stderr
        if "libx264" in encoder_text:
            encoder = "libx264"
        elif "h264_videotoolbox" in encoder_text:
            encoder = "h264_videotoolbox"
        add("render-encoder:h264", bool(encoder), encoder or "neither libx264 nor h264_videotoolbox is declared")
        add("render-encoder:aac", "aac" in encoder_text, "aac" if "aac" in encoder_text else "aac is not declared")
        if encoder:
            with tempfile.TemporaryDirectory(prefix="audio-first-doctor-") as temporary:
                smoke = Path(temporary) / "smoke.mp4"
                command = [
                    str(render_ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=0.2",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.2",
                    "-c:v", encoder,
                ]
                if encoder == "libx264":
                    command.extend(["-preset", "ultrafast"])
                else:
                    command.extend(["-allow_sw", "1"])
                command.extend(["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", str(smoke)])
                encoded = subprocess.run(command, text=True, capture_output=True, env=env, timeout=60)
                smoke_ok = encoded.returncode == 0 and smoke.is_file() and smoke.stat().st_size > 0
                smoke_detail = f"{encoder} + AAC" if smoke_ok else (encoded.stderr or encoded.stdout)[-500:].strip()
                add("render-smoke:h264-aac", smoke_ok, smoke_detail)
    node_ok, node_version = execute([str(bin_dir / "node"), "--version"], env)
    major = int(re.search(r"(\d+)", node_version).group(1)) if node_ok and re.search(r"(\d+)", node_version) else 0
    add("node>=22", major >= 22, node_version)

    probe = (
        "import importlib.metadata as m, json; "
        "print(json.dumps({n:m.version(n) for n in ['dashscope','faster-whisper','ctranslate2']}))"
    )
    ok, detail = execute([str(bin_dir / "python"), "-c", probe], env)
    add("python-packages", ok, detail)
    model = Path(os.environ.get("AUDIO_FIRST_WHISPER_MODEL", root / "models/faster-whisper-small"))
    required_model_files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
    missing = [name for name in required_model_files if not (model / name).is_file()]
    add("whisper-model-files", not missing, str(model) if not missing else f"missing: {', '.join(missing)}")
    if args.deep and not missing:
        deep_env = dict(env)
        deep_env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
        code = f"from faster_whisper import WhisperModel; WhisperModel({str(model)!r}, device='cpu', compute_type='int8'); print('loaded offline')"
        ok, detail = execute([str(bin_dir / "python"), "-c", code], deep_env)
        add("whisper-offline-load", ok, detail)

    whisper_cpp_model_value = env.get("AUDIO_FIRST_WHISPER_CPP_MODEL", "")
    whisper_cpp_model = Path(whisper_cpp_model_value).resolve() if whisper_cpp_model_value else None
    whisper_cpp = bin_dir / "whisper-cli"
    whisper_cpp_configured = whisper_cpp_model is not None
    add("whisper-cpp-binary", whisper_cpp.is_file() and os.access(whisper_cpp, os.X_OK), str(whisper_cpp), required=whisper_cpp_configured)
    add("whisper-cpp-model", bool(whisper_cpp_model and whisper_cpp_model.is_file()), str(whisper_cpp_model or "not configured"), required=whisper_cpp_configured)
    if whisper_cpp.is_file():
        ok, detail = execute([str(whisper_cpp), "--version"], env)
        add("run:whisper-cpp", ok, detail, required=whisper_cpp_configured)

    chrome_root = Path.home() / ".cache/hyperframes/chrome"
    chrome = next((path for path in chrome_root.glob("**/chrome-headless-shell") if path.is_file() and os.access(path, os.X_OK)), None) if chrome_root.is_dir() else None
    add("hyperframes-chrome", chrome is not None, str(chrome) if chrome else "not found")
    credentials = all(os.environ.get(name) for name in ("DASHSCOPE_API_KEY", "DASHSCOPE_WORKSPACE_ID", "DASHSCOPE_API_HOST"))
    csv_value = os.environ.get("DASHSCOPE_CREDENTIALS_CSV", "")
    csv_ready = bool(csv_value and Path(csv_value).is_file())
    add("dashscope-credentials", credentials or csv_ready, "configured" if credentials or csv_ready else "set provider env vars or DASHSCOPE_CREDENTIALS_CSV", required=False)
    playwright_value = os.environ.get("AUDIO_FIRST_PLAYWRIGHT_ROOT", "")
    playwright_root = Path(playwright_value) if playwright_value else None
    add("optional-playwright", bool(playwright_root and playwright_root.is_dir()), str(playwright_root) if playwright_root else "set AUDIO_FIRST_PLAYWRIGHT_ROOT when needed", required=False)

    required_failures = [item for item in checks if item["required"] and not item["passed"]]
    payload = {"status": "ready" if not required_failures else "failed", "toolchain": str(root), "checks": checks}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"toolchain: {root}\nstatus: {payload['status']}")
        for item in checks:
            marker = "✓" if item["passed"] else ("!" if not item["required"] else "✗")
            print(f"{marker} {item['name']}: {item['detail']}")
    return 1 if required_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
