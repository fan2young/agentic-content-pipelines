#!/usr/bin/env python3
"""Verify the exact FFmpeg render path with a real H.264/AAC smoke encode."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from pipeline_utils import digest, load_manifest, now_iso, write_json


DEFAULT_TOOLCHAIN = Path.home() / ".local/share/audio-first-video/toolchain"


def run(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout)


def first_line(result: subprocess.CompletedProcess[str]) -> str:
    value = (result.stdout.strip() or result.stderr.strip()).splitlines()
    return value[0] if value else f"exit {result.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--ffmpeg", type=Path)
    parser.add_argument("--ffprobe", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--prefer-hardware", action="store_true", help="prefer VideoToolbox over libx264 when its real smoke encode succeeds")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = args.project.resolve()
    toolchain = Path(os.environ.get("AUDIO_FIRST_TOOLCHAIN", DEFAULT_TOOLCHAIN)).resolve()
    ffmpeg = (args.ffmpeg or Path(os.environ.get("AUDIO_FIRST_RENDER_FFMPEG", os.environ.get("HYPERFRAMES_FFMPEG_PATH", toolchain / "bin/ffmpeg")))).resolve()
    ffprobe = (args.ffprobe or Path(os.environ.get("AUDIO_FIRST_RENDER_FFPROBE", os.environ.get("HYPERFRAMES_FFPROBE_PATH", ffmpeg.with_name("ffprobe"))))).resolve()
    # A CLI --ffmpeg value is a hard pin. Environment values are toolchain
    # preferences and must remain eligible for deterministic fallback when the
    # preferred binary only exposes an unusable hardware encoder.
    explicit_runtime = bool(args.ffmpeg)
    system_ffmpeg = Path(shutil.which("ffmpeg") or "").resolve() if shutil.which("ffmpeg") else None
    system_ffprobe = Path(shutil.which("ffprobe") or "").resolve() if shutil.which("ffprobe") else None
    if not explicit_runtime and system_ffmpeg and system_ffprobe and system_ffmpeg != ffmpeg:
        preferred_has_libx264 = False
        if ffmpeg.is_file():
            preferred_inventory = run([str(ffmpeg), "-hide_banner", "-encoders"])
            preferred_has_libx264 = "libx264" in (preferred_inventory.stdout + preferred_inventory.stderr)
        system_inventory = run([str(system_ffmpeg), "-hide_banner", "-encoders"])
        system_has_libx264 = "libx264" in (system_inventory.stdout + system_inventory.stderr)
        if not preferred_has_libx264 and system_has_libx264:
            ffmpeg, ffprobe = system_ffmpeg, system_ffprobe
    output = (args.output or root / "runtime-preflight.json").resolve()
    expected_delivery = {"width": args.width, "height": args.height, "fps": args.fps, "videoCodec": "h264", "pixelFormat": "yuv420p", "audioCodec": "aac", "sampleRate": 48000, "channels": 2}
    if output.is_file() and not args.force and ffmpeg.is_file() and ffprobe.is_file():
        previous = json.loads(output.read_text(encoding="utf-8"))
        previous_runtime = previous.get("runtime", {})
        unchanged = (
            previous.get("status") == "ready" and previous.get("delivery") == expected_delivery
            and previous_runtime.get("ffmpeg", {}).get("sha256") == digest(ffmpeg)
            and previous_runtime.get("ffprobe", {}).get("sha256") == digest(ffprobe)
            and previous_runtime.get("hardwarePreferred", False) == args.prefer_hardware
        )
        if unchanged:
            manifest_path, manifest = load_manifest(root)
            manifest.setdefault("stages", {})["runtime_preflight"] = "ready"
            write_json(manifest_path, manifest)
            print(json.dumps({"status": "ready", "cached": True, "output": str(output)}, ensure_ascii=False))
            return 0
    checks: list[dict] = []
    errors: list[str] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            errors.append(f"{name}: {detail}")

    add("ffmpeg_exists", ffmpeg.is_file() and os.access(ffmpeg, os.X_OK), str(ffmpeg))
    add("ffprobe_exists", ffprobe.is_file() and os.access(ffprobe, os.X_OK), str(ffprobe))
    encoder = ""
    ffmpeg_version = ""
    ffprobe_version = ""
    if not errors:
        ffmpeg_result = run([str(ffmpeg), "-version"])
        ffprobe_result = run([str(ffprobe), "-version"])
        ffmpeg_version = first_line(ffmpeg_result)
        ffprobe_version = first_line(ffprobe_result)
        add("ffmpeg_runs", ffmpeg_result.returncode == 0, ffmpeg_version)
        add("ffprobe_runs", ffprobe_result.returncode == 0, ffprobe_version)

    if not errors:
        encoder_result = run([str(ffmpeg), "-hide_banner", "-encoders"])
        encoder_text = encoder_result.stdout + encoder_result.stderr
        add("encoder_inventory", encoder_result.returncode == 0, "queried FFmpeg encoders")
        if args.prefer_hardware and "h264_videotoolbox" in encoder_text:
            encoder = "h264_videotoolbox"
        elif "libx264" in encoder_text:
            encoder = "libx264"
        elif "h264_videotoolbox" in encoder_text:
            encoder = "h264_videotoolbox"
        add("h264_encoder_declared", bool(encoder), encoder or "neither libx264 nor h264_videotoolbox is declared")
        add("aac_encoder_declared", "aac" in encoder_text, "aac" if "aac" in encoder_text else "aac is not declared")

    if not errors:
        with tempfile.TemporaryDirectory(prefix="audio-first-render-preflight-") as temporary:
            target = Path(temporary) / "smoke.mp4"
            command = [
                str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={args.width}x{args.height}:r={args.fps}:d=0.2",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.2",
                "-c:v", encoder,
            ]
            if encoder == "libx264":
                command.extend(["-preset", "ultrafast"])
            elif encoder == "h264_videotoolbox":
                command.extend(["-allow_sw", "1"])
            command.extend(["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", str(target)])
            encoded = run(command, timeout=60)
            if encoded.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
                detail = (encoded.stderr or encoded.stdout)[-1200:].strip() or f"exit {encoded.returncode}"
                add("delivery_smoke_encode", False, detail)
            else:
                add("delivery_smoke_encode", True, f"{encoder} + AAC produced {target.stat().st_size} bytes")
                probed = run([str(ffprobe), "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate,sample_rate,channels", "-of", "json", str(target)])
                try:
                    probe_data = json.loads(probed.stdout)
                except json.JSONDecodeError:
                    probe_data = {}
                streams = probe_data.get("streams", [])
                video = next((item for item in streams if item.get("codec_name") == "h264"), {})
                audio = next((item for item in streams if item.get("codec_name") == "aac"), {})
                verified = (
                    video.get("width") == args.width and video.get("height") == args.height
                    and video.get("r_frame_rate") == f"{args.fps}/1"
                    and audio.get("sample_rate") == "48000" and audio.get("channels") == 2
                )
                add("delivery_stream_contract", verified, json.dumps({"video": video, "audio": audio}, ensure_ascii=False))

    payload = {
        "schemaVersion": 1,
        "status": "ready" if not errors else "failed",
        "createdAt": now_iso(),
        "runtime": {
            "ffmpeg": {"path": str(ffmpeg), "sha256": digest(ffmpeg) if ffmpeg.is_file() else "", "version": ffmpeg_version},
            "ffprobe": {"path": str(ffprobe), "sha256": digest(ffprobe) if ffprobe.is_file() else "", "version": ffprobe_version},
            "videoEncoder": encoder,
            "hardwarePreferred": args.prefer_hardware,
        },
        "delivery": expected_delivery,
        "checks": checks,
        "actionableExceptions": errors,
    }
    write_json(output, payload)

    manifest_path, manifest = load_manifest(root)
    manifest.setdefault("stages", {})["runtime_preflight"] = payload["status"]
    try:
        relative = str(output.relative_to(root))
    except ValueError:
        relative = str(output)
    manifest.setdefault("outputs", {})["runtimePreflight"] = relative
    manifest.setdefault("history", []).append({
        "at": now_iso(), "event": "runtime_preflight", "status": payload["status"],
        "ffmpeg": str(ffmpeg), "videoEncoder": encoder,
    })
    write_json(manifest_path, manifest)
    print(json.dumps({"status": payload["status"], "cached": False, "videoEncoder": encoder, "actionableExceptions": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
