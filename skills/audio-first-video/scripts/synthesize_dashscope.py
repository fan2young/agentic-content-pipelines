#!/usr/bin/env python3
"""Generate a 24 kHz mono WAV narration with Bailian/DashScope TTS."""

from __future__ import annotations

import argparse
import csv
import io
import os
import wave
from pathlib import Path
from urllib.parse import urlparse

import dashscope
from dashscope.audio.tts_v2 import AudioFormat, SpeechSynthesizer


DEFAULT_MODEL = "qwen-audio-3.0-tts-flash"
DEFAULT_VOICE = "longanhuan_v3.6"
OFFICIAL_API_HOSTS = {"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com"}


def read_credentials_csv(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Credentials CSV not found: {path}")
    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2:
                values[row[0].strip()] = row[1].strip()
    return values


def normalize_api_host(value: str, allow_custom: bool) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("DASHSCOPE_API_HOST must be an HTTPS host.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("DASHSCOPE_API_HOST must not contain credentials, query, or fragment.")
    if parsed.path not in {"", "/"} or parsed.port not in {None, 443}:
        raise ValueError("DASHSCOPE_API_HOST must not contain a custom path or port.")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname not in OFFICIAL_API_HOSTS and not allow_custom:
        raise ValueError(
            "Refusing a non-DashScope host. Re-run with --allow-custom-api-host "
            "only after verifying and approving the destination."
        )
    return hostname


def load_credentials(csv_path: Path | None, allow_custom_host: bool = False) -> tuple[str, str, str]:
    values = read_credentials_csv(csv_path) if csv_path else {}
    api_key = os.environ.get("DASHSCOPE_API_KEY") or values.get("apiKey", "")
    workspace_id = os.environ.get("DASHSCOPE_WORKSPACE_ID") or values.get(
        "workspaceId", ""
    )
    api_host = os.environ.get("DASHSCOPE_API_HOST") or values.get("apiHost", "")
    if not api_key:
        raise ValueError("Set DASHSCOPE_API_KEY or pass --credentials-csv.")
    if not workspace_id:
        raise ValueError("Set DASHSCOPE_WORKSPACE_ID or pass --credentials-csv.")
    if not api_host:
        raise ValueError("Set DASHSCOPE_API_HOST or pass --credentials-csv.")

    api_host = normalize_api_host(api_host, allow_custom_host)
    return api_key, workspace_id, f"wss://{api_host}/api-ws/v1/inference"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Approved UTF-8 narration file")
    source.add_argument("--text", help="Short text for a connectivity test")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--credentials-csv",
        type=Path,
        default=(
            Path(os.environ["DASHSCOPE_CREDENTIALS_CSV"])
            if os.environ.get("DASHSCOPE_CREDENTIALS_CSV")
            else None
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speech-rate", type=float, default=1.0)
    parser.add_argument("--pitch-rate", type=float, default=1.0)
    parser.add_argument("--volume", type=int, default=50)
    parser.add_argument(
        "--allow-custom-api-host",
        action="store_true",
        help="Allow an explicitly reviewed non-DashScope HTTPS host.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text = args.text if args.text is not None else args.input.read_text(encoding="utf-8")
    text = text.strip()
    if not text:
        raise ValueError("Synthesis text is empty.")

    api_key, workspace_id, websocket_url = load_credentials(
        args.credentials_csv, args.allow_custom_api_host
    )
    dashscope.api_key = api_key
    synthesizer = SpeechSynthesizer(
        model=args.model,
        voice=args.voice,
        format=AudioFormat.PCM_24000HZ_MONO_16BIT,
        volume=args.volume,
        speech_rate=args.speech_rate,
        pitch_rate=args.pitch_rate,
        workspace=workspace_id,
        url=websocket_url,
    )
    try:
        pcm_audio = synthesizer.call(text)
    except Exception as error:
        response = synthesizer.last_response or {}
        header = response.get("header", {})
        code = header.get("error_code") or header.get("code") or "unknown"
        message = header.get("error_message") or header.get("message") or str(error)
        request_id = header.get("task_id") or synthesizer.get_last_request_id()
        raise RuntimeError(
            f"DashScope TTS failed: code={code}; message={message}; "
            f"request_id={request_id}"
        ) from error
    if not pcm_audio:
        raise RuntimeError("DashScope returned no PCM audio data.")

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_audio)
    audio = wav_buffer.getvalue()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_output.write_bytes(audio)
    temporary_output.replace(args.output)
    print(f"output={args.output.resolve()}")
    print(f"bytes={len(audio)}")
    print(f"request_id={synthesizer.get_last_request_id()}")
    print(f"first_packet_delay_ms={synthesizer.get_first_package_delay()}")


if __name__ == "__main__":
    main()
