#!/usr/bin/env python3
"""Inspect narration audio with ffprobe and ffmpeg without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_loudness(stderr: str) -> dict[str, float | None]:
    integrated = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", stderr)
    true_peaks = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", stderr)
    return {
        "integratedLufs": float(integrated[-1]) if integrated else None,
        "truePeakDbtp": float(true_peaks[-1]) if true_peaks else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    audio = args.audio.resolve()
    if not audio.is_file():
        parser.error(f"audio not found: {audio}")
    for program in ("ffprobe", "ffmpeg"):
        if not shutil.which(program):
            parser.error(f"{program} is required and was not found")

    probe = run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,format_name,bit_rate:stream=index,codec_type,codec_name,sample_rate,channels,channel_layout",
        "-of", "json", str(audio),
    ])
    metadata = json.loads(probe.stdout)
    audio_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"), {})

    loudness = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        text=True,
        capture_output=True,
    )
    if loudness.returncode != 0:
        print(loudness.stderr, file=sys.stderr)
        return loudness.returncode

    result = {
        "path": str(audio),
        "sha256": sha256(audio),
        "duration": round(float(metadata.get("format", {}).get("duration", 0)), 6),
        "format": metadata.get("format", {}).get("format_name"),
        "codec": audio_stream.get("codec_name"),
        "sampleRate": int(audio_stream["sample_rate"]) if audio_stream.get("sample_rate") else None,
        "channels": audio_stream.get("channels"),
        "channelLayout": audio_stream.get("channel_layout"),
        **parse_loudness(loudness.stderr),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
