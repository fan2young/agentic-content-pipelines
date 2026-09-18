#!/usr/bin/env python3
"""Transcribe audio for timing, then align authoritative script text to ASR anchors."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


IGNORED = re.compile(r"[\s\u3000，。！？；：、“”‘’（）()《》〈〉【】\[\]…—,.!?;:'\"\-]")


def normalized_chars(text: str) -> list[str]:
    return [char.lower() for char in text if not IGNORED.fullmatch(char)]


def split_caption_text(text: str, max_chars: int) -> list[str]:
    compact = re.sub(r"[ \t\r\f\v]+", "", text).strip()
    units = [part.strip() for part in re.findall(r"[^。！？!?；;\n]+[。！？!?；;]?", compact) if part.strip()]
    result: list[str] = []
    for unit in units:
        while len(normalized_chars(unit)) > max_chars:
            candidates = [m.end() for m in re.finditer(r"[，、,:：]", unit)]
            cut = max((p for p in candidates if len(normalized_chars(unit[:p])) <= max_chars), default=0)
            if not cut:
                visible = 0
                cut = len(unit)
                for index, char in enumerate(unit):
                    if normalized_chars(char):
                        visible += 1
                    if visible >= max_chars:
                        cut = index + 1
                        break
            result.append(unit[:cut].strip())
            unit = unit[cut:].strip()
        if unit:
            result.append(unit)
    return result


DEFAULT_WHISPER_CPP_MODEL = Path.home() / ".local/share/audio-first-video/toolchain/models/ggml-small-q5_1.bin"


def transcribe_faster_whisper(audio: Path, script: str, model_name: str, language: str) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise SystemExit("faster-whisper is required: install it in the active Python environment") from error

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(audio), language=language, task="transcribe", beam_size=5, temperature=0,
        word_timestamps=True, vad_filter=True, vad_parameters={"min_silence_duration_ms": 180},
        condition_on_previous_text=False, initial_prompt=script,
    )
    output = {"engine": "faster-whisper-cpu", "language": info.language, "languageProbability": info.language_probability, "duration": info.duration, "segments": []}
    for segment in segments:
        output["segments"].append({
            "start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text.strip(),
            "words": [
                {"start": round(word.start, 3), "end": round(word.end, 3), "text": word.word.strip(), "probability": round(word.probability, 4)}
                for word in (segment.words or []) if word.word.strip()
            ],
        })
    return output


def transcribe_whisper_cpp(audio: Path, script: str, model: Path, language: str, executable: Path, threads: int) -> dict:
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError(f"whisper.cpp executable is unavailable: {executable}")
    if not model.is_file():
        raise RuntimeError(f"whisper.cpp model is unavailable: {model}")
    with tempfile.TemporaryDirectory(prefix="audio-first-whisper-cpp-") as temporary:
        prefix = Path(temporary) / "transcript"
        command = [
            str(executable), "--model", str(model), "--file", str(audio),
            "--language", language, "--threads", str(threads),
            "--beam-size", "5", "--best-of", "5", "--temperature", "0",
            "--prompt", script, "--output-json-full", "--output-file", str(prefix),
            "--no-prints",
        ]
        completed = subprocess.run(command, text=True, capture_output=True)
        result_path = prefix.with_suffix(".json")
        if completed.returncode != 0 or not result_path.is_file():
            detail = (completed.stderr or completed.stdout)[-1600:].strip()
            raise RuntimeError(f"whisper.cpp transcription failed: {detail or completed.returncode}")
        source = json.loads(result_path.read_text(encoding="utf-8"))

    result = source.get("result", {})
    output = {
        "engine": "whisper.cpp-metal",
        "model": str(model),
        "language": result.get("language", language),
        "languageProbability": result.get("language_probability", 1.0),
        "duration": 0.0,
        "segments": [],
    }
    for item in source.get("transcription", []):
        offsets = item.get("offsets", {})
        start = float(offsets.get("from", 0)) / 1000
        end = float(offsets.get("to", 0)) / 1000
        token_records = []
        for token in item.get("tokens", []):
            text = str(token.get("text", "")).strip()
            normalized = normalized_chars(text)
            if not normalized or text.startswith("[_") or text.startswith("<|"):
                continue
            token_offsets = token.get("offsets", {})
            token_start = float(token_offsets.get("from", offsets.get("from", 0))) / 1000
            token_end = float(token_offsets.get("to", offsets.get("to", 0))) / 1000
            seconds_per_character = (token_end - token_start) / len(normalized)
            valid = start <= token_start < token_end <= end and seconds_per_character <= 1.0
            token_records.append({
                "start": token_start, "end": token_end,
                "text": text, "probability": round(float(token.get("p", 1.0)), 4),
                "characters": len(normalized), "valid": valid,
            })
        cursor = 0
        while cursor < len(token_records):
            if token_records[cursor]["valid"]:
                cursor += 1
                continue
            block_end = cursor
            while block_end < len(token_records) and not token_records[block_end]["valid"]:
                block_end += 1
            left = token_records[cursor - 1]["end"] if cursor else start
            right = token_records[block_end]["start"] if block_end < len(token_records) else end
            total_characters = sum(record["characters"] for record in token_records[cursor:block_end])
            step = max(0.001, right - left) / max(1, total_characters)
            character_cursor = 0
            for record in token_records[cursor:block_end]:
                record["start"] = left + step * character_cursor
                character_cursor += record["characters"]
                record["end"] = left + step * character_cursor
                record["valid"] = True
            cursor = block_end
        words = [{
            "start": round(record["start"], 3), "end": round(record["end"], 3),
            "text": record["text"], "probability": record["probability"],
        } for record in token_records]
        output["segments"].append({
            "start": round(start, 3), "end": round(end, 3),
            "text": str(item.get("text", "")).strip(), "words": words,
        })
        output["duration"] = max(float(output["duration"]), end)
    if not output["segments"]:
        raise RuntimeError("whisper.cpp returned no transcription segments")
    return output


def asr_character_anchors(raw: dict) -> tuple[list[str], list[tuple[float, float]]]:
    chars: list[str] = []
    spans: list[tuple[float, float]] = []
    for segment in raw["segments"]:
        words = segment.get("words") or [{"text": segment["text"], "start": segment["start"], "end": segment["end"]}]
        for word in words:
            token = normalized_chars(word["text"])
            if not token:
                continue
            start, end = float(word["start"]), float(word["end"])
            width = max(0.001, end - start) / len(token)
            for index, char in enumerate(token):
                chars.append(char)
                spans.append((start + width * index, start + width * (index + 1)))
    return chars, spans


def interpolate(source: list[str], anchors: list[str], spans: list[tuple[float, float]], duration: float) -> tuple[list[tuple[float, float]], int]:
    mapped: list[tuple[float, float] | None] = [None] * len(source)
    matcher = SequenceMatcher(a=source, b=anchors, autojunk=False)
    matched = 0
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            mapped[block.a + offset] = spans[block.b + offset]
            matched += 1

    known = [index for index, value in enumerate(mapped) if value is not None]
    if not known:
        raise SystemExit("No usable alignment anchors were found")
    for index in range(len(mapped)):
        if mapped[index] is not None:
            continue
        left = max((k for k in known if k < index), default=None)
        right = min((k for k in known if k > index), default=None)
        if left is None:
            right_start = mapped[right][0]  # type: ignore[index]
            step = right_start / max(1, right + 1)
            mapped[index] = (step * index, step * (index + 1))
        elif right is None:
            left_end = mapped[left][1]  # type: ignore[index]
            step = (duration - left_end) / max(1, len(mapped) - left)
            mapped[index] = (left_end + step * (index - left - 1), left_end + step * (index - left))
        else:
            left_end = mapped[left][1]  # type: ignore[index]
            right_start = mapped[right][0]  # type: ignore[index]
            step = max(0.001, right_start - left_end) / (right - left)
            mapped[index] = (left_end + step * (index - left - 1), left_end + step * (index - left))
    return [value for value in mapped if value is not None], matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=os.environ.get("AUDIO_FIRST_WHISPER_MODEL", "small"))
    parser.add_argument("--engine", choices=("auto", "faster-whisper", "whisper-cpp"), default="auto")
    parser.add_argument("--whisper-cli", type=Path, default=Path(shutil.which("whisper-cli") or "/opt/homebrew/bin/whisper-cli"))
    parser.add_argument("--whisper-cpp-model", type=Path, default=Path(os.environ.get("AUDIO_FIRST_WHISPER_CPP_MODEL", DEFAULT_WHISPER_CPP_MODEL)))
    parser.add_argument("--threads", type=int, default=min(12, os.cpu_count() or 4))
    parser.add_argument("--language", default="zh")
    parser.add_argument("--max-chars", type=int, default=16)
    parser.add_argument("--confidence-threshold", type=float, default=0.7)
    parser.add_argument("--min-caption-duration", type=float, default=0.45)
    parser.add_argument("--max-caption-duration", type=float, default=4.5)
    args = parser.parse_args()

    script = args.script.read_text(encoding="utf-8").strip()
    source_chars = normalized_chars(script)
    if not source_chars:
        parser.error("script contains no alignable characters")
    requested_engine = args.engine
    engine = requested_engine
    if engine == "auto":
        engine = "whisper-cpp" if args.whisper_cli.is_file() and args.whisper_cpp_model.is_file() else "faster-whisper"
    started = time.perf_counter()
    if engine == "whisper-cpp":
        try:
            raw = transcribe_whisper_cpp(args.audio.resolve(), script, args.whisper_cpp_model.resolve(), args.language, args.whisper_cli.resolve(), args.threads)
        except RuntimeError as error:
            if requested_engine != "auto":
                raise SystemExit(str(error)) from error
            raw = transcribe_faster_whisper(args.audio.resolve(), script, args.model, args.language)
            raw["fallbackReason"] = str(error)
    else:
        raw = transcribe_faster_whisper(args.audio.resolve(), script, args.model, args.language)
    elapsed_seconds = round(time.perf_counter() - started, 3)
    anchor_chars, anchor_spans = asr_character_anchors(raw)
    char_spans, matched = interpolate(source_chars, anchor_chars, anchor_spans, float(raw["duration"]))

    captions = []
    cursor = 0
    for index, text in enumerate(split_caption_text(script, args.max_chars), start=1):
        length = len(normalized_chars(text))
        if not length:
            continue
        span = char_spans[cursor:cursor + length]
        cursor += length
        captions.append({"id": f"c{index:03d}", "start": round(span[0][0], 3), "end": round(span[-1][1], 3), "text": text})

    for index in range(len(captions) - 1):
        if captions[index]["end"] > captions[index + 1]["start"]:
            midpoint = round((captions[index]["end"] + captions[index + 1]["start"]) / 2, 3)
            captions[index]["end"] = midpoint
            captions[index + 1]["start"] = midpoint

    ratio = matched / len(source_chars)
    low_confidence_words = []
    for segment in raw["segments"]:
        for word in segment.get("words", []):
            if not normalized_chars(str(word.get("text", ""))):
                continue
            probability = float(word.get("probability", 1.0))
            if probability < args.confidence_threshold:
                low_confidence_words.append({
                    "start": word["start"], "end": word["end"], "text": word["text"],
                    "probability": round(probability, 4),
                })
    duration_exceptions = []
    for caption in captions:
        caption_duration = round(float(caption["end"]) - float(caption["start"]), 3)
        if caption_duration < args.min_caption_duration or caption_duration > args.max_caption_duration:
            duration_exceptions.append({
                "id": caption["id"], "duration": caption_duration, "text": caption["text"],
            })
    warnings = []
    if ratio < 0.72:
        warnings.append("Low character match ratio; manually review caption timing.")
    if low_confidence_words:
        warnings.append(f"Review {len(low_confidence_words)} low-confidence ASR word anchors.")
    if duration_exceptions:
        warnings.append(f"Review {len(duration_exceptions)} captions outside the preferred duration range.")
    needs_review = ratio < 0.72 or bool(low_confidence_words) or bool(duration_exceptions)
    report = {
        "engine": raw.get("engine", engine), "requestedEngine": requested_engine,
        "fallbackReason": raw.get("fallbackReason", ""), "elapsedSeconds": elapsed_seconds,
        "sourceCharacters": len(source_chars), "asrCharacters": len(anchor_chars), "matchedCharacters": matched,
        "matchRatio": round(ratio, 4), "status": "review" if needs_review else "ready",
        "warnings": warnings,
        "exceptions": {
            "lowConfidenceWords": low_confidence_words,
            "captionDuration": duration_exceptions,
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "raw-asr.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {"version": 1, "audio": args.audio.name, "duration": round(float(raw["duration"]), 6), "captions": captions}
    (args.output_dir / "captions.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "alignment-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    console_report = {
        "status": report["status"], "matchRatio": report["matchRatio"],
        "exceptionCounts": {
            "lowConfidenceWords": len(low_confidence_words),
            "captionDuration": len(duration_exceptions),
        },
        "warnings": warnings,
    }
    print(json.dumps(console_report, ensure_ascii=False, indent=2))
    return 0 if ratio >= 0.55 else 2


if __name__ == "__main__":
    raise SystemExit(main())
