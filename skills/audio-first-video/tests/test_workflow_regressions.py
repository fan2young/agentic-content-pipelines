from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], text=True, capture_output=True)


class WorkflowRegressionTests(unittest.TestCase):
    @staticmethod
    def write_silence(path: Path, seconds: float) -> None:
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(b"\x00\x00" * int(24000 * seconds))

    def test_audio_router_requires_dashscope_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "manifest.json").write_text(json.dumps({
                "schemaVersion": 2,
                "project": {"contextOrchestration": {"status": "approved"}},
                "stages": {"audio_lock": "pending"},
                "outputs": {},
            }), encoding="utf-8")
            result = run_script("next_action.py", str(project), "--context", "audio_timing")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("references/dashscope-tts.md", payload["requiredReads"])
            self.assertIn("synthesize_dashscope.py", payload["command"])

    def test_non_dashscope_lock_requires_explicit_provider_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            candidate = project / "candidate.wav"
            candidate.write_bytes(b"not-a-real-wave")
            candidate_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
            (project / "manifest.json").write_text(json.dumps({
                "schemaVersion": 2, "audio": {}, "stages": {"audio_lock": "pending"}, "outputs": {}, "history": []
            }), encoding="utf-8")
            result = run_script(
                "lock_audio.py", str(project), str(candidate), "--approve", "--provider", "macos-say",
                "--confirmed-sha256", candidate_hash,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-DashScope narration requires", result.stderr)

    def test_candidate_fingerprint_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            candidate = project / "candidate.wav"
            candidate.write_bytes(b"candidate")
            (project / "manifest.json").write_text(json.dumps({
                "schemaVersion": 2, "audio": {}, "stages": {"audio_lock": "pending"}, "outputs": {}, "history": []
            }), encoding="utf-8")
            result = run_script(
                "lock_audio.py", str(project), str(candidate), "--approve", "--provider", "dashscope",
                "--model", "qwen-audio-3.0-tts-flash", "--voice", "longanhuan_v3.6",
                "--confirmed-sha256", "0" * 64,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match", result.stderr)

    def test_large_replacement_duration_change_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            first = project / "first.wav"
            second = project / "second.wav"
            self.write_silence(first, 1.0)
            self.write_silence(second, 1.5)
            (project / "manifest.json").write_text(json.dumps({
                "schemaVersion": 2, "audio": {}, "stages": {"audio_lock": "pending"}, "outputs": {}, "history": []
            }), encoding="utf-8")
            first_hash = hashlib.sha256(first.read_bytes()).hexdigest()
            result = run_script(
                "lock_audio.py", str(project), str(first), "--approve", "--provider", "dashscope",
                "--model", "qwen-audio-3.0-tts-flash", "--voice", "longanhuan_v3.6",
                "--confirmed-sha256", first_hash,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            second_hash = hashlib.sha256(second.read_bytes()).hexdigest()
            result = run_script(
                "lock_audio.py", str(project), str(second), "--approve", "--replace", "--provider", "dashscope",
                "--model", "qwen-audio-3.0-tts-flash", "--voice", "longanhuan_v3.6",
                "--confirmed-sha256", second_hash,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("replacement duration changed", result.stderr)

    def test_recent_episode_discovery_copies_real_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            library = Path(tmp)
            current = library / "video-production" / "2026-08-03-current" / "project"
            current.mkdir(parents=True)
            for date in ("2026-08-01", "2026-08-02"):
                episode = library / "daily-production" / date / "project"
                episode.mkdir(parents=True)
                (episode / "manifest.json").write_text("{}", encoding="utf-8")
                (episode / "DESIGN.md").write_text(f"# {date}\n", encoding="utf-8")
                (episode / "final.mp4").write_bytes(b"video")
                (episode / "review-scenes-sheet.png").write_bytes(b"frame")
            result = run_script("discover_recent_video_references.py", str(current), "--library-root", str(library))
            self.assertEqual(result.returncode, 0, result.stderr)
            ledger = json.loads((current / "brand-references.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["availableEpisodeCount"], 2)
            self.assertEqual(ledger["copiedEpisodeCount"], 2)
            self.assertEqual(ledger["episodes"][0]["date"], "2026-08-02")
            for episode in ledger["episodes"]:
                self.assertTrue((current / episode["designPath"]).is_file())
                self.assertTrue((current / episode["framePaths"][0]).is_file())

    def test_visual_direction_cannot_be_model_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ledger = {"schemaVersion": 1, "status": "ready", "availableEpisodeCount": 0, "copiedEpisodeCount": 0, "episodes": []}
            ledger_path = project / "brand-references.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            frames = []
            for role in ("opening", "core-mechanism", "close"):
                path = project / f"{role}.png"
                path.write_bytes(b"frame")
                frames.append({"role": role, "path": path.name})
            proof = {
                "schemaVersion": 1, "status": "approved",
                "brandReferencesSha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                "frames": frames,
                "comparison": {key: "对照最近频道视觉并保持一致" for key in ("palette", "typography", "logo", "materialLanguage", "density", "motionGrammar")},
                "checks": {"recentEpisodesCompared": True, "warmPaperInkRedDefault": True, "completeLockupPresent": True, "editorialMaterialLanguage": True, "redAxisHasMeaning": True, "noGenericAiTheme": True},
                "approvedBy": "model:auto", "approvedAt": "2026-08-13T00:00:00Z",
            }
            proof["comparison"]["deviationReason"] = ""
            proof_path = project / "visual-direction-proof.json"
            proof_path.write_text(json.dumps(proof), encoding="utf-8")
            result = run_script("validate_visual_direction.py", str(proof_path))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("model:auto is forbidden", result.stdout)
            proof["approvedBy"] = "user"
            proof_path.write_text(json.dumps(proof), encoding="utf-8")
            result = run_script("validate_visual_direction.py", str(proof_path))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
