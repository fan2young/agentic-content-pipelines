#!/usr/bin/env python3
"""Encode the locked narration through the delivery audio path and verify loudness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from pipeline_utils import digest, load_manifest, now_iso, resolve_media_runtime, write_json


def parse_ebur128(stderr: str) -> tuple[float | None, float | None]:
    integrated = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", stderr)
    peaks = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", stderr)
    return (float(integrated[-1]) if integrated else None, float(peaks[-1]) if peaks else None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path, default=Path("delivery-audio-preflight.json"))
    parser.add_argument("--channels", type=int, default=2)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--bitrate", default="192k")
    parser.add_argument("--min-lufs", type=float, default=-19.0)
    parser.add_argument("--max-lufs", type=float, default=-16.0)
    parser.add_argument("--max-true-peak", type=float, default=-1.0)
    parser.add_argument("--keep-media", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--upstream-audio", type=Path, help="Locked narration when audio is a normalized delivery derivative")
    parser.add_argument("--no-normalize", action="store_false", dest="normalize", help="Measure without the standard delivery loudness normalization")
    parser.set_defaults(normalize=True)
    args = parser.parse_args()
    audio = args.audio.resolve()
    if not audio.is_file():
        parser.error(f"audio not found: {audio}")
    upstream = args.upstream_audio.resolve() if args.upstream_audio else audio
    if not upstream.is_file():
        parser.error(f"upstream audio not found: {upstream}")
    project_root = args.output.resolve().parent
    try:
        ffmpeg, _ = resolve_media_runtime(project_root)
    except RuntimeError as error:
        parser.error(str(error))
    expected = {
        "sourceSha256": digest(audio), "upstreamSourceSha256": digest(upstream),
        "encoded": {"codec": "aac", "channels": args.channels, "sampleRate": args.sample_rate, "bitrate": args.bitrate, "normalized": args.normalize},
        "targets": {"minLufs": args.min_lufs, "maxLufs": args.max_lufs, "maxTruePeakDbtp": args.max_true_peak},
    }
    output_path = args.output.resolve()
    if output_path.is_file() and not args.force:
        previous = json.loads(output_path.read_text(encoding="utf-8"))
        if previous.get("status") == "ready" and all(previous.get(key) == value for key, value in expected.items()):
            print(json.dumps({"status": "ready", "cached": True, "output": str(output_path)}, ensure_ascii=False))
            return 0
    with tempfile.TemporaryDirectory(prefix="delivery-audio-") as directory:
        encoded = Path(directory) / "delivery.m4a"
        encode_command = [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio),
            "-vn", "-ac", str(args.channels), "-ar", str(args.sample_rate),
        ]
        if args.normalize:
            encode_command.extend(["-af", "loudnorm=I=-18:TP=-1.5:LRA=11"])
        encode_command.extend(["-c:a", "aac", "-b:a", args.bitrate, str(encoded)])
        encode = subprocess.run(encode_command, capture_output=True, text=True)
        if encode.returncode:
            raise SystemExit(encode.stderr.strip() or "delivery audio encode failed")
        measurement = subprocess.run([
            str(ffmpeg), "-hide_banner", "-nostats", "-i", str(encoded), "-filter_complex", "ebur128=peak=true", "-f", "null", "-",
        ], capture_output=True, text=True)
        if measurement.returncode:
            raise SystemExit(measurement.stderr.strip() or "delivery audio measurement failed")
        integrated, true_peak = parse_ebur128(measurement.stderr)
        exceptions = []
        if integrated is None:
            exceptions.append("integrated loudness could not be measured")
        elif not args.min_lufs <= integrated <= args.max_lufs:
            exceptions.append(f"integrated loudness {integrated} LUFS is outside {args.min_lufs}..{args.max_lufs}")
        if true_peak is None:
            exceptions.append("true peak could not be measured")
        elif true_peak > args.max_true_peak:
            exceptions.append(f"true peak {true_peak} dBTP exceeds {args.max_true_peak} dBTP")
        payload = {
            "schemaVersion": 1, "status": "failed" if exceptions else "ready", "source": str(audio),
            "sourceSha256": expected["sourceSha256"], "upstreamSourceSha256": expected["upstreamSourceSha256"], "encoded": expected["encoded"],
            "integratedLufs": integrated, "truePeakDbtp": true_peak,
            "targets": expected["targets"],
            "actionableExceptions": exceptions,
        }
        if args.keep_media:
            args.keep_media.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(encoded, args.keep_media)
            payload["encodedMedia"] = str(args.keep_media)
        write_json(args.output, payload)
        manifest_path = args.output.resolve().parent / "manifest.json"
        if manifest_path.is_file():
            path, manifest = load_manifest(args.output.resolve().parent)
            manifest.setdefault("outputs", {})["deliveryAudioPreflight"] = args.output.name
            manifest.setdefault("history", []).append({"at": now_iso(), "event": "delivery_audio_preflight", "status": payload["status"]})
            write_json(path, manifest)
    print(json.dumps({"status": payload["status"], "cached": False, "actionableExceptions": exceptions}, ensure_ascii=False, indent=2))
    return 1 if exceptions else 0


if __name__ == "__main__":
    raise SystemExit(main())
