#!/usr/bin/env python3
"""Build draft scene ranges from corrected captions and an optional scene outline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from pipeline_utils import digest, invalidate, load_manifest, now_iso, write_json


def normalized(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value).lower()


def choose_boundaries(captions: list[dict], draft_scenes: list[dict], count: int, duration: float) -> tuple[list[int], list[dict]]:
    boundaries: list[int] = []
    diagnostics: list[dict] = []
    previous = 0
    for scene_index in range(1, count):
        target = duration * scene_index / count
        minimum = previous + 1
        maximum = len(captions) - (count - scene_index)
        candidates = range(minimum, maximum + 1)
        draft = draft_scenes[scene_index] if scene_index < len(draft_scenes) else {}
        anchor_id = str(draft.get("startCaptionId", "")).strip()
        anchor_phrase = normalized(str(draft.get("startPhrase", "")))
        matches = []
        if anchor_id:
            matches = [i for i in candidates if str(captions[i].get("id")) == anchor_id]
        elif anchor_phrase:
            matches = [i for i in candidates if anchor_phrase in normalized(str(captions[i].get("text", "")))]
        if len(matches) == 1:
            best = matches[0]
            method = "startCaptionId" if anchor_id else "startPhrase"
        else:
            best = min(candidates, key=lambda i: abs(float(captions[i]["start"]) - target) - min(2.0, max(0.0, float(captions[i]["start"]) - float(captions[i - 1]["end"]))) * 0.75)
            method = "pause_heuristic"
        boundaries.append(best)
        diagnostics.append({
            "scene": draft.get("id", f"s{scene_index + 1:02d}"), "captionId": captions[best].get("id"),
            "method": method, "requestedAnchor": anchor_id or draft.get("startPhrase"),
            "warning": None if method != "pause_heuristic" else "add a unique startPhrase to remove heuristic review",
        })
        previous = best
    return boundaries, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captions", type=Path, required=True)
    parser.add_argument("--scene-draft", type=Path)
    parser.add_argument("--scene-count", type=int)
    parser.add_argument("--tail-pad", type=float, default=0.5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    caption_data = json.loads(args.captions.read_text(encoding="utf-8"))
    captions = caption_data.get("captions", [])
    if not captions:
        parser.error("captions file contains no captions")
    draft_scenes = []
    if args.scene_draft:
        draft_scenes = json.loads(args.scene_draft.read_text(encoding="utf-8")).get("scenes", [])
    count = args.scene_count or len(draft_scenes) or max(3, min(9, round(float(caption_data["duration"]) / 14)))
    if count > len(captions):
        parser.error("scene count cannot exceed caption count")

    audio_duration = float(caption_data["duration"])
    composition_duration = round(audio_duration + args.tail_pad, 3)
    boundaries, diagnostics = choose_boundaries(captions, draft_scenes, count, audio_duration)
    indexes = [0, *boundaries, len(captions)]
    cuts = [round(float(captions[index]["start"]), 3) for index in indexes[1:-1]]
    starts = [0.0, *cuts]
    ends = [*cuts, composition_duration]
    ranges = []
    for index, (start, end) in enumerate(zip(starts, ends)):
        draft = draft_scenes[index] if index < len(draft_scenes) else {}
        ranges.append({
            "scene": draft.get("id", f"s{index + 1:02d}"), "start": start, "end": end,
            "beat": draft.get("beat", f"Scene {index + 1}"),
        })
    output = {
        "version": 1, "audio": caption_data.get("audio"), "audioDuration": audio_duration,
        "compositionDuration": composition_duration, "tailPad": args.tail_pad,
        "sceneTransitions": cuts, "sceneRanges": ranges,
        "boundaryDiagnostics": diagnostics,
    }
    old_hash = digest(args.output) if args.output.is_file() else ""
    write_json(args.output, output)
    manifest_path = args.output.resolve().parent / "manifest.json"
    if manifest_path.is_file():
        path, manifest = load_manifest(args.output.resolve().parent)
        new_hash = digest(args.output)
        if old_hash and old_hash != new_hash:
            invalidate(manifest, "timing", "timing.json SHA-256 changed")
        manifest.setdefault("stages", {})["timing"] = "ready"
        manifest.setdefault("outputs", {})["timing"] = args.output.name
        manifest.setdefault("history", []).append({"at": now_iso(), "event": "timing_built", "sha256": new_hash})
        write_json(path, manifest)
    print(json.dumps({
        "status": "ready", "audioDuration": audio_duration,
        "compositionDuration": composition_duration, "sceneCount": len(ranges),
        "transitionCount": len(cuts), "output": str(args.output),
        "heuristicBoundaryCount": sum(item["method"] == "pause_heuristic" for item in diagnostics),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
