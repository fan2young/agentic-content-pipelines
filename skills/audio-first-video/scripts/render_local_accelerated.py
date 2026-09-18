#!/usr/bin/env python3
"""Render a HyperFrames composition with the fingerprinted local runtime and browser GPU."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


DEFAULT_TOOLCHAIN = Path.home() / ".local/share/audio-first-video/toolchain"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="project containing runtime-preflight.json")
    parser.add_argument("composition", type=Path, help="HyperFrames composition directory")
    parser.add_argument("output", type=Path)
    parser.add_argument("--runtime-report", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--toolchain", type=Path, default=DEFAULT_TOOLCHAIN)
    parser.add_argument("--require-hardware-encode", action="store_true")
    parser.add_argument("--software-browser", action="store_true")
    parser.add_argument("--workers", default="auto")
    parser.add_argument("--quality", choices=("draft", "standard", "high"), default="high")
    args = parser.parse_args()

    project = args.project.resolve()
    composition = args.composition.resolve()
    output = args.output.resolve()
    runtime_report = (args.runtime_report or project / "runtime-preflight.json").resolve()
    report_path = (args.report or output.with_suffix(output.suffix + ".render-report.json")).resolve()
    runtime = json.loads(runtime_report.read_text(encoding="utf-8"))
    if runtime.get("status") != "ready":
        raise SystemExit(f"runtime preflight is not ready: {runtime_report}")

    recorded = runtime.get("runtime", {})
    ffmpeg_record = recorded.get("ffmpeg", {})
    ffprobe_record = recorded.get("ffprobe", {})
    ffmpeg = Path(ffmpeg_record.get("path", "")).resolve()
    ffprobe = Path(ffprobe_record.get("path", "")).resolve()
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise SystemExit("recorded FFmpeg/FFprobe pair is missing")
    if digest(ffmpeg) != ffmpeg_record.get("sha256") or digest(ffprobe) != ffprobe_record.get("sha256"):
        raise SystemExit("recorded render runtime fingerprint changed; rerun preflight")

    encoder = recorded.get("videoEncoder", "")
    hardware_encode = encoder == "h264_videotoolbox"
    if args.require_hardware_encode and not hardware_encode:
        raise SystemExit("hardware encoding is required but runtime-preflight.json did not approve h264_videotoolbox")

    hyperframes = (args.toolchain.resolve() / "bin/hyperframes")
    if not hyperframes.is_file():
        raise SystemExit(f"missing HyperFrames launcher: {hyperframes}")
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.stem}-", suffix=output.suffix, dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()

    command = [
        str(hyperframes), "render", str(composition),
        "--output", str(temporary), "--quality", args.quality,
        "--workers", args.workers,
    ]
    browser_mode = "software" if args.software_browser else "hardware"
    command.append("--no-browser-gpu" if args.software_browser else "--browser-gpu")
    if not args.software_browser:
        command.append("--experimental-fast-capture")
    if hardware_encode:
        command.append("--gpu")

    environment = dict(os.environ)
    environment["HYPERFRAMES_FFMPEG_PATH"] = str(ffmpeg)
    environment["HYPERFRAMES_FFPROBE_PATH"] = str(ffprobe)
    environment["AUDIO_FIRST_RENDER_FFMPEG"] = str(ffmpeg)
    environment["AUDIO_FIRST_RENDER_FFPROBE"] = str(ffprobe)
    environment["PRODUCER_BROWSER_GPU_MODE"] = browser_mode
    environment["PRODUCER_EXPERIMENTAL_FAST_CAPTURE"] = "false" if args.software_browser else "true"

    started = time.perf_counter()
    completed = subprocess.run(command, text=True, capture_output=True, env=environment)
    elapsed = round(time.perf_counter() - started, 3)
    success = completed.returncode == 0 and temporary.is_file() and temporary.stat().st_size > 0
    payload = {
        "schemaVersion": 1,
        "status": "ready" if success else "failed",
        "composition": str(composition),
        "output": str(output),
        "elapsedSeconds": elapsed,
        "browserGpuMode": browser_mode,
        "fastCaptureRequested": not args.software_browser,
        "videoEncoder": encoder,
        "hardwareEncode": hardware_encode,
        "runtimeReport": str(runtime_report),
        "ffmpegSha256": digest(ffmpeg),
        "exitCode": completed.returncode,
        "diagnosticTail": (completed.stderr or completed.stdout)[-2000:],
    }
    if success:
        os.replace(temporary, output)
        payload["outputSha256"] = digest(output)
        payload["sizeBytes"] = output.stat().st_size
    elif temporary.exists():
        temporary.unlink()
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "elapsedSeconds", "browserGpuMode", "videoEncoder", "hardwareEncode", "exitCode")}, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
