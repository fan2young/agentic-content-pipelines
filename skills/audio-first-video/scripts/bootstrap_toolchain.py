#!/usr/bin/env python3
"""Build a stable, offline-rebuildable media toolchain."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile


DEFAULT_ROOT = Path.home() / ".local/share/audio-first-video/toolchain"


def run(command: list[str], env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
    return result.stdout.strip() or result.stderr.strip()


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def replace_symlink(link: Path, target: Path) -> None:
    if link.is_symlink():
        if link.resolve() == target.resolve():
            return
        link.unlink()
    elif link.exists():
        raise FileExistsError(f"refusing to replace non-symlink: {link}")
    link.symlink_to(os.path.relpath(target, link.parent))


def copy_tree(source: Path, destination: Path, dereference: bool = False, reuse_existing: bool = False) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    if source.resolve() == destination.resolve():
        return
    if reuse_existing and destination.is_dir() and any(destination.iterdir()):
        return
    shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=not dereference)


def copy_file(source: Path, destination: Path) -> None:
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def validate_render_pair(ffmpeg: Path, ffprobe: Path) -> dict:
    """Require a real delivery-shaped H.264/AAC encode, not inventory alone."""
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise FileNotFoundError("render FFmpeg/FFprobe pair is incomplete")
    inventory = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-encoders"],
        text=True,
        capture_output=True,
        timeout=30,
    )
    if inventory.returncode != 0:
        raise RuntimeError((inventory.stderr or inventory.stdout).strip() or "FFmpeg encoder inventory failed")
    encoder_text = inventory.stdout + inventory.stderr
    encoders = [name for name in ("libx264", "h264_videotoolbox") if name in encoder_text]
    if "aac" not in encoder_text or not encoders:
        raise RuntimeError("render runtime must declare AAC and libx264 or h264_videotoolbox")
    failures: list[str] = []
    for encoder in encoders:
        with tempfile.TemporaryDirectory(prefix="audio-first-bootstrap-smoke-") as temporary:
            target = Path(temporary) / "smoke.mp4"
            command = [
                str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=0.2",
                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.2",
                "-c:v", encoder,
            ]
            if encoder == "libx264":
                command.extend(["-preset", "ultrafast"])
            else:
                command.extend(["-allow_sw", "1"])
            command.extend([
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-ar", "48000", "-ac", "2", "-shortest", str(target),
            ])
            encoded = subprocess.run(command, text=True, capture_output=True, timeout=60)
            if encoded.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
                detail = (encoded.stderr or encoded.stdout)[-800:].strip() or f"exit {encoded.returncode}"
                failures.append(f"{encoder}: {detail}")
                continue
            probed = subprocess.run(
                [str(ffprobe), "-v", "error", "-show_entries", "stream=codec_name,width,height,r_frame_rate,sample_rate,channels", "-of", "json", str(target)],
                text=True,
                capture_output=True,
                timeout=30,
            )
            try:
                streams = json.loads(probed.stdout).get("streams", [])
            except json.JSONDecodeError:
                streams = []
            video = next((item for item in streams if item.get("codec_name") == "h264"), {})
            audio = next((item for item in streams if item.get("codec_name") == "aac"), {})
            verified = (
                video.get("width") == 1080 and video.get("height") == 1920
                and video.get("r_frame_rate") == "30/1"
                and audio.get("sample_rate") == "48000" and audio.get("channels") == 2
            )
            if verified:
                return {"videoEncoder": encoder, "bytes": target.stat().st_size, "deliveryVerified": True}
            failures.append(f"{encoder}: encoded streams failed the delivery contract")
    raise RuntimeError("; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--ffmpeg-dir", type=Path, required=True, help="directory containing native ffmpeg and ffprobe")
    parser.add_argument("--node-dir", type=Path, required=True, help="Node distribution root containing bin/node")
    parser.add_argument("--hyperframes-dir", type=Path, required=True, help="existing HyperFrames project with node_modules")
    parser.add_argument("--whisper-model", type=Path, required=True, help="resolved faster-whisper model snapshot")
    parser.add_argument("--whisper-cpp-model", type=Path, help="optional pinned ggml whisper.cpp model")
    parser.add_argument("--whisper-cli", type=Path, help="optional whisper.cpp CLI; defaults to PATH")
    parser.add_argument("--skip-wheelhouse", action="store_true")
    parser.add_argument("--python-site-packages", type=Path, help="clone a verified same-version Python environment instead of downloading")
    parser.add_argument("--render-ffmpeg", type=Path, help="verified FFmpeg used by HyperFrames; defaults to the bundled FFmpeg")
    parser.add_argument("--render-ffprobe", type=Path, help="matching FFprobe; defaults beside --render-ffmpeg")
    args = parser.parse_args()

    root = args.root.resolve()
    skill_root = Path(__file__).resolve().parents[1]
    requirements = skill_root / "requirements-runtime.txt"
    media = root / "media/bin"
    node = root / "node"
    hyperframes = root / "hyperframes"
    model = root / "models/faster-whisper-small"
    whisper_cpp_model = root / "models/ggml-small-q5_1.bin"
    wheelhouse = root / "wheelhouse"
    venv = root / "python"
    bin_dir = root / "bin"
    for directory in (media, hyperframes, model, wheelhouse, bin_dir, root / "lib"):
        directory.mkdir(parents=True, exist_ok=True)

    for name in ("ffmpeg", "ffprobe"):
        source = args.ffmpeg_dir.resolve() / name
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = media / name
        copy_file(source, destination)
        destination.chmod(destination.stat().st_mode | 0o111)
    copy_tree(args.node_dir.resolve(), node, reuse_existing=True)
    source_hyperframes = args.hyperframes_dir.resolve()
    copy_tree(source_hyperframes / "node_modules", hyperframes / "node_modules", reuse_existing=True)
    for name in ("package.json", "pnpm-lock.yaml"):
        source = source_hyperframes / name
        if source.is_file():
            copy_file(source, hyperframes / name)
    copy_tree(args.whisper_model.resolve(), model, dereference=True, reuse_existing=True)
    if args.whisper_cpp_model:
        copy_file(args.whisper_cpp_model.resolve(), whisper_cpp_model)
    shutil.copy2(requirements, root / "requirements-runtime.txt")
    shutil.copy2(Path(__file__).with_name("check_environment.py"), root / "lib/check_environment.py")
    shutil.copy2(Path(__file__).with_name("render_local_accelerated.py"), root / "lib/render_local_accelerated.py")

    if not (venv / "bin/python").is_file():
        run([sys.executable, "-m", "venv", str(venv)])
    python = venv / "bin/python"
    pip = venv / "bin/pip"
    install_method = "wheelhouse"
    if args.python_site_packages:
        version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        destination_packages = venv / "lib" / version / "site-packages"
        copy_tree(args.python_site_packages.resolve(), destination_packages)
        install_method = "verified-site-packages-clone"
    elif args.skip_wheelhouse:
        run([str(pip), "install", "--disable-pip-version-check", "-r", str(requirements)])
        install_method = "online-pip"
    else:
        run([str(pip), "download", "--disable-pip-version-check", "-r", str(requirements), "-d", str(wheelhouse)])
        run([str(pip), "install", "--disable-pip-version-check", "--no-index", "--find-links", str(wheelhouse), "-r", str(requirements)])

    for name, target in (("python", python), ("pip", pip)):
        launcher = bin_dir / name
        if launcher.is_symlink():
            launcher.unlink()
        launcher.write_text(f"#!/bin/sh\nexec '{target}' \"$@\"\n", encoding="utf-8")
        launcher.chmod(0o755)
    replace_symlink(bin_dir / "ffmpeg", media / "ffmpeg")
    replace_symlink(bin_dir / "ffprobe", media / "ffprobe")
    replace_symlink(bin_dir / "node", node / "bin/node")
    replace_symlink(bin_dir / "npm", node / "bin/npm")
    replace_symlink(bin_dir / "npx", node / "bin/npx")
    whisper_cli_value = args.whisper_cli.resolve() if args.whisper_cli else Path(shutil.which("whisper-cli") or "")
    if whisper_cli_value.is_file():
        replace_symlink(bin_dir / "whisper-cli", whisper_cli_value.resolve())
    hyperframes_launcher = bin_dir / "hyperframes"
    if hyperframes_launcher.is_symlink():
        hyperframes_launcher.unlink()
    hyperframes_launcher.write_text(
        "#!/bin/sh\n"
        f". '{root / 'env.sh'}'\n"
        f"exec '{node / 'bin/node'}' '{hyperframes / 'node_modules/hyperframes/bin/hyperframes.mjs'}' \"$@\"\n",
        encoding="utf-8",
    )
    hyperframes_launcher.chmod(0o755)

    env_file = root / "env.sh"
    credentials = Path.home() / ".config/audio-first-finance-video/dashscope.csv"
    credentials_export = f"export DASHSCOPE_CREDENTIALS_CSV='{credentials}'\n" if credentials.is_file() else ""
    whisper_cpp_export = f"export AUDIO_FIRST_WHISPER_CPP_MODEL='{whisper_cpp_model}'\n" if whisper_cpp_model.is_file() else ""
    render_candidates: list[tuple[Path, Path]] = []
    if args.render_ffmpeg:
        requested_ffmpeg = args.render_ffmpeg.resolve()
        requested_ffprobe = (args.render_ffprobe or requested_ffmpeg.with_name("ffprobe")).resolve()
        render_candidates.append((requested_ffmpeg, requested_ffprobe))
    else:
        render_candidates.append((media / "ffmpeg", media / "ffprobe"))
        system_ffmpeg = shutil.which("ffmpeg")
        system_ffprobe = shutil.which("ffprobe")
        if system_ffmpeg and system_ffprobe:
            system_pair = (Path(system_ffmpeg).resolve(), Path(system_ffprobe).resolve())
            if system_pair != tuple(path.resolve() for path in render_candidates[0]):
                render_candidates.append(system_pair)
    render_ffmpeg = Path()
    render_ffprobe = Path()
    render_smoke: dict = {}
    render_failures: list[str] = []
    for candidate_ffmpeg, candidate_ffprobe in render_candidates:
        try:
            candidate_smoke = validate_render_pair(candidate_ffmpeg.resolve(), candidate_ffprobe.resolve())
        except (FileNotFoundError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            render_failures.append(f"{candidate_ffmpeg}: {error}")
            continue
        render_ffmpeg, render_ffprobe, render_smoke = candidate_ffmpeg.resolve(), candidate_ffprobe.resolve(), candidate_smoke
        break
    if not render_smoke:
        raise RuntimeError("no render runtime passed H.264/AAC smoke encode: " + " | ".join(render_failures))
    # bin/ffmpeg is the fixed toolchain's render authority. Keep the copied
    # media binary under media/bin for provenance, but never expose an
    # unverified hardware-only binary through the public launcher.
    replace_symlink(bin_dir / "ffmpeg", render_ffmpeg)
    replace_symlink(bin_dir / "ffprobe", render_ffprobe)
    env_file.write_text(
        "#!/bin/sh\n"
        f"export AUDIO_FIRST_TOOLCHAIN='{root}'\n"
        f"export AUDIO_FIRST_WHISPER_MODEL='{model}'\n"
        f"{whisper_cpp_export}"
        f"{credentials_export}"
        "export PRODUCER_BROWSER_GPU_MODE='hardware'\n"
        "export PRODUCER_EXPERIMENTAL_FAST_CAPTURE='true'\n"
        f"export AUDIO_FIRST_RENDER_FFMPEG='{render_ffmpeg}'\n"
        f"export AUDIO_FIRST_RENDER_FFPROBE='{render_ffprobe}'\n"
        'export HYPERFRAMES_FFMPEG_PATH="$AUDIO_FIRST_RENDER_FFMPEG"\n'
        'export HYPERFRAMES_FFPROBE_PATH="$AUDIO_FIRST_RENDER_FFPROBE"\n'
        f"export PATH='{bin_dir}':\"$PATH\"\n",
        encoding="utf-8",
    )
    env_file.chmod(0o755)
    doctor = bin_dir / "audio-first-doctor"
    doctor.write_text(
        "#!/bin/sh\n"
        f". '{env_file}'\n"
        f"exec '{python}' '{root / 'lib/check_environment.py'}' --toolchain '{root}' \"$@\"\n",
        encoding="utf-8",
    )
    doctor.chmod(0o755)

    command_env = dict(os.environ)
    command_env["PATH"] = f"{bin_dir}:{command_env.get('PATH', '')}"
    inventory = {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "paths": {"root": str(root), "bin": str(bin_dir), "python": str(python), "whisperModel": str(model), "whisperCppModel": str(whisper_cpp_model) if whisper_cpp_model.is_file() else "", "whisperCli": str(whisper_cli_value.resolve()) if whisper_cli_value.is_file() else "", "renderFfmpeg": str(render_ffmpeg), "renderFfprobe": str(render_ffprobe)},
        "renderSmoke": render_smoke,
        "pythonInstallMethod": install_method,
        "versions": {
            "python": run([str(python), "--version"]),
            "node": run([str(bin_dir / "node"), "--version"]),
            "ffmpeg": run([str(bin_dir / "ffmpeg"), "-version"]).splitlines()[0],
            "ffprobe": run([str(bin_dir / "ffprobe"), "-version"]).splitlines()[0],
            "renderFfmpeg": run([str(render_ffmpeg), "-version"]).splitlines()[0],
            "renderFfprobe": run([str(render_ffprobe), "-version"]).splitlines()[0],
            "hyperframes": run([str(bin_dir / "hyperframes"), "--version"], env=command_env),
        },
        "sha256": {"ffmpeg": sha256(media / "ffmpeg"), "ffprobe": sha256(media / "ffprobe"), "whisperCppModel": sha256(whisper_cpp_model) if whisper_cpp_model.is_file() else "", "renderFfmpeg": sha256(render_ffmpeg), "renderFfprobe": sha256(render_ffprobe)},
    }
    temporary = root / "toolchain.json.tmp"
    temporary.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(root / "toolchain.json")
    print(json.dumps({"status": "ready", **inventory}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
