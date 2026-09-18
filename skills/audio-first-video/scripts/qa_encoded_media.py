#!/usr/bin/env python3
"""Create a compact, schema-backed QA report for an encoded release candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from pipeline_utils import digest, load_manifest, now_iso, resolve_media_runtime, write_json


def rate(value: str) -> float:
    numerator, denominator = value.split("/") if "/" in value else (value, "1")
    return float(numerator) / float(denominator)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--output", type=Path, default=Path("review-report.json"))
    parser.add_argument("--timing", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--min-lufs", type=float, default=-19.0)
    parser.add_argument("--max-lufs", type=float, default=-16.0)
    parser.add_argument("--max-true-peak", type=float, default=-1.0)
    parser.add_argument("--visual-review", type=Path, help="JSON with scenesReviewed, transitionsReviewed, firstFrame, finalSpokenFrame, finalFrame")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    media = args.media.resolve()
    if not media.is_file():
        parser.error(f"media not found: {media}")
    try:
        ffmpeg, ffprobe = resolve_media_runtime(args.output.resolve().parent)
    except RuntimeError as error:
        parser.error(str(error))
    visual_review = json.loads(args.visual_review.read_text(encoding="utf-8")) if args.visual_review else {"status": "pending"}
    inputs = {
        "mediaSha256": digest(media),
        "timingSha256": digest(args.timing.resolve()) if args.timing else None,
        "visualReviewSha256": digest(args.visual_review.resolve()) if args.visual_review else None,
        "runtime": {"ffmpegSha256": digest(ffmpeg), "ffprobeSha256": digest(ffprobe)},
        "targets": {"width": args.width, "height": args.height, "minLufs": args.min_lufs, "maxLufs": args.max_lufs, "maxTruePeakDbtp": args.max_true_peak},
    }
    output_path = args.output.resolve()
    if output_path.is_file() and not args.force:
        previous = json.loads(output_path.read_text(encoding="utf-8"))
        if previous.get("status") == "ready" and previous.get("inputs") == inputs:
            print(json.dumps({"status": "ready", "cached": True, "file": media.name, "sha256": inputs["mediaSha256"]}, ensure_ascii=False))
            return 0
    probe = subprocess.run([
        str(ffprobe), "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels,channel_layout",
        "-of", "json", str(media),
    ], check=True, capture_output=True, text=True)
    metadata = json.loads(probe.stdout)
    video = next((item for item in metadata.get("streams", []) if item.get("codec_type") == "video"), {})
    audio = next((item for item in metadata.get("streams", []) if item.get("codec_type") == "audio"), {})
    duration = float(metadata.get("format", {}).get("duration", 0))
    measurement = subprocess.run([
        str(ffmpeg), "-hide_banner", "-nostats", "-i", str(media), "-filter_complex", "ebur128=peak=true", "-f", "null", "-",
    ], capture_output=True, text=True)
    integrated_values = re.findall(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", measurement.stderr)
    peak_values = re.findall(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", measurement.stderr)
    integrated = float(integrated_values[-1]) if integrated_values else None
    true_peak = float(peak_values[-1]) if peak_values else None
    black = subprocess.run([
        str(ffmpeg), "-hide_banner", "-nostats", "-i", str(media), "-vf", "blackdetect=d=0.20:pix_th=0.10", "-an", "-f", "null", "-",
    ], capture_output=True, text=True)
    black_intervals = [{"start": float(a), "end": float(b), "duration": float(c)} for a, b, c in re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)", black.stderr)]
    checks: list[dict] = []
    exceptions: list[str] = []
    def check(name: str, passed: bool, passed_detail: str, failed_detail: str) -> None:
        detail = passed_detail if passed else failed_detail
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            exceptions.append(detail)
    check("dimensions", video.get("width") == args.width and video.get("height") == args.height, f"dimensions are {args.width}x{args.height}", f"expected {args.width}x{args.height}; got {video.get('width')}x{video.get('height')}")
    check("audio_stream", bool(audio), "audio stream is present", "encoded candidate has no audio stream")
    check("loudness", integrated is not None and args.min_lufs <= integrated <= args.max_lufs, f"integrated loudness is {integrated} LUFS", f"integrated loudness {integrated} LUFS is outside {args.min_lufs}..{args.max_lufs}")
    check("true_peak", true_peak is not None and true_peak <= args.max_true_peak, f"true peak is {true_peak} dBTP", f"true peak {true_peak} dBTP exceeds {args.max_true_peak} dBTP")
    black_adjudicated = visual_review.get("blackIntervals") == "approved"
    check("black_frames", not black_intervals or black_adjudicated, "no unreviewed black intervals", f"detected {len(black_intervals)} unreviewed black interval(s)")
    if args.timing:
        timing = json.loads(args.timing.read_text(encoding="utf-8"))
        expected = float(timing["compositionDuration"])
        check("duration", abs(duration - expected) <= 0.10, f"container duration matches timing within 0.10s", f"container duration {duration:.3f}s differs from timing {expected:.3f}s")
    automatic_failed = bool(exceptions)
    visual_pending = visual_review.get("status") != "approved"
    if int(visual_review.get("schemaVersion", 1)) >= 2:
        review_checks = visual_review.get("checks", {})
        if review_checks.get("logoAssetExact") is not True:
            exceptions.append("encoded visual review must confirm the official logo asset is exact")
            visual_pending = True
        if review_checks.get("logoAxisIsolation") is not True:
            exceptions.append("encoded visual review must confirm logo axes do not merge with narrative lines")
            visual_pending = True
    if visual_pending:
        exceptions.append("visual review must be explicitly approved")
    status = "failed" if automatic_failed or visual_pending else "ready"
    report = {
        "schemaVersion": 2, "status": status, "file": media.name, "sha256": inputs["mediaSha256"], "sizeBytes": media.stat().st_size,
        "inputs": inputs,
        "containerDurationSeconds": round(duration, 6),
        "video": {"codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"), "frameRate": round(rate(video.get("avg_frame_rate", "0/1")), 6)},
        "audio": {"codec": audio.get("codec_name"), "sampleRate": int(audio["sample_rate"]) if audio.get("sample_rate") else None, "channels": audio.get("channels"), "channelLayout": audio.get("channel_layout"), "integratedLufs": integrated, "truePeakDbtp": true_peak},
        "qa": {"checks": checks, "actionableExceptions": exceptions, "blackIntervals": black_intervals, "visualReview": visual_review},
        "approval": {"status": "pending"},
    }
    write_json(args.output, report)
    manifest_path = args.output.resolve().parent / "manifest.json"
    if manifest_path.is_file():
        path, manifest = load_manifest(args.output.resolve().parent)
        manifest.setdefault("stages", {})["video_review"] = "failed" if status == "failed" else "ready"
        manifest.setdefault("outputs", {}).update({"videoReview": media.name, "videoReviewReport": args.output.name})
        manifest.setdefault("history", []).append({"at": now_iso(), "event": "encoded_media_qa", "status": status, "sha256": report["sha256"]})
        write_json(path, manifest)
    print(json.dumps({"status": status, "cached": False, "file": media.name, "sha256": report["sha256"], "actionableExceptions": exceptions}, ensure_ascii=False, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
