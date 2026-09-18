#!/usr/bin/env python3
"""Validate the Next Variable creative video contract before rendering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

ENGINES = {"evidence-documentary", "spatial-mechanism", "interface-process", "human-work"}
REGISTERS = {"evidence", "mechanism", "interface", "human", "type-data"}
ASSET_TYPES = {"brand", "evidence", "photo", "footage", "ui", "mechanism", "type-data"}
SOURCE_TYPES = {"evidence", "photo", "footage", "ui"}
DESIGN_MARKERS = {
    "brand": ("brand invariants", "品牌不变量"),
    "engine": ("episode visual engine", "本期视觉引擎"),
    "assets": ("asset mix", "素材结构"),
    "motion": ("motion arc", "动效弧线"),
    "audit": ("anti-repetition", "跨期去重", "latest three", "最近三期"),
    "negative": ("what not to do", "禁止事项"),
}
GENERIC_MOTION = ("元素依次动画", "元素动画进入", "依次出现", "animate in", "elements enter")


def load_scenes(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    for key in ("scenes", "items"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError("scenes-draft.json must be a list or contain a scenes/items list")


def load_asset_ledger(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assets = data.get("assets") if isinstance(data, dict) else None
    if not isinstance(assets, list):
        raise ValueError("asset-ledger.json must contain an assets list")
    ledger: dict[str, dict] = {}
    for index, asset in enumerate(assets, 1):
        if not isinstance(asset, dict) or not isinstance(asset.get("id"), str) or not asset["id"].strip():
            raise ValueError(f"asset-ledger.json asset {index} has no valid id")
        if asset["id"] in ledger:
            raise ValueError(f"asset-ledger.json duplicates id {asset['id']}")
        ledger[asset["id"]] = asset
    return ledger


def local_asset_exists(project: Path, value: str) -> bool:
    if value.startswith("inline:"):
        file_part = value.removeprefix("inline:").split("#", 1)[0]
        return bool(file_part) and (project / file_part).exists()
    return (project / value).exists()


def load_caption_ids(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    captions = data if isinstance(data, list) else data.get("captions", [])
    if not isinstance(captions, list):
        raise ValueError("captions.json must be a list or contain a captions list")
    return {item["id"] for item in captions if isinstance(item, dict) and isinstance(item.get("id"), str)}


def load_source_visuals(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    visuals = data.get("visuals", [])
    if not isinstance(visuals, list):
        raise ValueError("source-visuals.json must contain a visuals list")
    return {
        item["id"]: item
        for item in visuals
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    project = args.project_dir.resolve()
    design_path = project / "DESIGN.md"
    scenes_path = project / "scenes-draft.json"
    ledger_path = project / "asset-ledger.json"
    captions_path = project / "captions.json"
    source_visuals_path = project / "source-visuals.json"
    timing_path = project / "timing.json"
    brand_references_path = project / "brand-references.json"
    errors: list[str] = []
    warnings: list[str] = []

    if not design_path.exists():
        errors.append("missing DESIGN.md")
        design = ""
    else:
        design = design_path.read_text(encoding="utf-8").lower()
        for name, markers in DESIGN_MARKERS.items():
            if not any(marker in design for marker in markers):
                warnings.append(f"DESIGN.md may be missing {name} declaration")
        if not any(term in design for term in ("persistent", "常驻", "brand bug")):
            errors.append("DESIGN.md does not declare a persistent brand marker")
        if not all(term in design for term in ("opening", "midpoint", "close")) and not all(
            term in design for term in ("开场", "中段", "结尾")
        ):
            errors.append("brand visibility at opening, midpoint, and close is not explicit")

    if not scenes_path.exists():
        errors.append("missing scenes-draft.json")
        scenes = []
    else:
        try:
            scenes = load_scenes(scenes_path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            scenes = []

    try:
        scene_document = json.loads(scenes_path.read_text(encoding="utf-8")) if scenes_path.exists() else {}
    except json.JSONDecodeError:
        scene_document = {}
    if not isinstance(scene_document, dict):
        scene_document = {}

    if not scenes:
        errors.append("scenes-draft.json contains no scenes")

    if not ledger_path.exists():
        errors.append("missing asset-ledger.json")
        ledger = {}
    else:
        try:
            ledger = load_asset_ledger(ledger_path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            ledger = {}

    if not captions_path.exists():
        errors.append("missing captions.json for claim ID validation")
        caption_ids = set()
    else:
        try:
            caption_ids = load_caption_ids(captions_path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            caption_ids = set()

    if source_visuals_path.exists():
        try:
            source_visuals = load_source_visuals(source_visuals_path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            source_visuals = {}
    else:
        warnings.append("missing source-visuals.json; legacy project cannot enforce shared source assets")
        source_visuals = None

    timing_document: dict = {}
    timing_ranges: list[dict] = []
    timing_by_scene: dict[str, dict] = {}
    if not timing_path.exists():
        errors.append("missing timing.json; canonical scene durations cannot be validated")
    else:
        try:
            timing_document = json.loads(timing_path.read_text(encoding="utf-8"))
            candidate_ranges = timing_document.get("sceneRanges", []) if isinstance(timing_document, dict) else []
            if not isinstance(candidate_ranges, list) or not candidate_ranges:
                errors.append("timing.json must contain non-empty sceneRanges")
            else:
                timing_ranges = candidate_ranges
                for item in timing_ranges:
                    scene_id = item.get("scene") if isinstance(item, dict) else None
                    if not isinstance(scene_id, str) or not scene_id.strip():
                        errors.append("timing.json sceneRanges contain an invalid scene id")
                    elif scene_id in timing_by_scene:
                        errors.append(f"timing.json duplicates scene {scene_id}")
                    else:
                        timing_by_scene[scene_id] = item
        except json.JSONDecodeError as exc:
            errors.append(f"invalid timing.json: {exc}")

    registers: list[str] = []
    engines: set[str] = set()
    total_duration = 0.0
    type_data_duration = 0.0
    referenced_assets: set[str] = set()
    engine_duration: dict[str, float] = {}
    scene_ids: set[str] = set()
    for index, scene in enumerate(scenes, 1):
        label = scene.get("id") or f"scene {index}"
        if not isinstance(scene.get("id"), str) or not scene["id"].strip() or scene["id"] in scene_ids:
            errors.append(f"{label}: scene id must be unique and non-empty")
        else:
            scene_ids.add(scene["id"])
        engine = scene.get("visualEngine")
        register = scene.get("visualRegister")
        if engine not in ENGINES:
            errors.append(f"{label}: invalid or missing visualEngine")
        else:
            engines.add(engine)
        if register not in REGISTERS:
            errors.append(f"{label}: invalid or missing visualRegister")
        else:
            registers.append(register)
        timing_range = timing_by_scene.get(scene.get("id"))
        start = timing_range.get("start") if timing_range else None
        end = timing_range.get("end") if timing_range else None
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
            errors.append(f"{label}: timing.json must define a positive scene duration")
            duration = 0.0
        else:
            duration = float(end - start)
            total_duration += duration
            if register == "type-data":
                type_data_duration += duration
            if engine in ENGINES:
                engine_duration[engine] = engine_duration.get(engine, 0.0) + duration
        mid_change = scene.get("midSceneChange")
        if duration >= 5 and (not isinstance(mid_change, str) or len(mid_change.strip()) < 12):
            errors.append(f"{label}: long scene is missing a concrete midSceneChange")
        elif duration < 5 and not isinstance(mid_change, str):
            owner = scene.get("motionArcOwner")
            if not isinstance(owner, str) or not owner.strip():
                errors.append(f"{label}: short scene needs midSceneChange or motionArcOwner")
        elif isinstance(mid_change, str) and any(phrase in mid_change.lower() for phrase in GENERIC_MOTION):
            errors.append(f"{label}: midSceneChange only describes a generic entrance")
        brand = scene.get("brandIntegration")
        if not isinstance(brand, str) or len(brand.strip()) < 8:
            errors.append(f"{label}: missing concrete brandIntegration")
        if not isinstance(scene.get("assetIds"), list):
            errors.append(f"{label}: assetIds must be a list")
        else:
            asset_ids = scene["assetIds"]
            if any(not isinstance(asset_id, str) or not asset_id.strip() for asset_id in asset_ids):
                errors.append(f"{label}: assetIds must contain non-empty strings")
            valid_ids = {asset_id for asset_id in asset_ids if isinstance(asset_id, str) and asset_id.strip()}
            referenced_assets.update(valid_ids)
            if not valid_ids:
                errors.append(f"{label}: scene has no traceable assetIds")
            for asset_id in sorted(valid_ids - ledger.keys()):
                errors.append(f"{label}: assetId {asset_id} is missing from asset-ledger.json")

    for i in range(len(registers) - 2):
        if registers[i : i + 3] == ["type-data"] * 3:
            errors.append(f"scenes {i + 1}-{i + 3}: more than two consecutive type-data beats")
    if len(engines) < 2:
        errors.append("composition must declare both a primary and secondary visual engine")
    elif total_duration and min(engine_duration.values()) / total_duration < 0.1:
        errors.append("secondary visual engine occupies less than 10% of the composition")
    if total_duration > 15 and type_data_duration / total_duration > 0.4:
        errors.append("type-data occupies more than 40% of the composition duration")
    scene_order = [scene.get("id") for scene in scenes if isinstance(scene, dict)]
    timing_order = [item.get("scene") for item in timing_ranges if isinstance(item, dict)]
    if timing_ranges and timing_order != scene_order:
        errors.append("timing.json sceneRanges must match scenes-draft.json scene order exactly")
    previous_end: float | None = None
    for index, item in enumerate(timing_ranges, 1):
        start, end = item.get("start"), item.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
            errors.append(f"timing.json sceneRanges[{index}] must define a positive duration")
            continue
        if previous_end is None and abs(float(start)) > 0.05:
            errors.append("timing.json timeline must start at 0")
        if previous_end is not None:
            if float(start) < previous_end - 0.01:
                errors.append(f"timing.json sceneRanges[{index}] overlaps the previous scene")
            elif float(start) > previous_end + 0.5:
                errors.append(f"timing.json sceneRanges[{index}] has an unexplained gap over 0.5 seconds")
        previous_end = float(end)
    declared_duration = timing_document.get("compositionDuration")
    if not isinstance(declared_duration, (int, float)) or declared_duration <= 0:
        errors.append("timing.json needs a positive compositionDuration")
    elif previous_end is not None and abs(previous_end - declared_duration) > 0.05:
        errors.append("timing.json timeline end does not match compositionDuration")

    brand_coverage = scene_document.get("brandCoverage")
    if not isinstance(brand_coverage, dict):
        errors.append("scenes-draft.json needs structured brandCoverage")
    else:
        brand_asset_id = brand_coverage.get("brandAssetId")
        if brand_asset_id not in ledger or ledger.get(brand_asset_id, {}).get("type") != "brand":
            errors.append("brandCoverage.brandAssetId must resolve to a brand asset")
        for position in ("openingScene", "midpointScene", "closeScene"):
            if brand_coverage.get(position) not in scene_ids:
                errors.append(f"brandCoverage.{position} must resolve to a scene id")

    scene_schema_version = int(scene_document.get("schemaVersion", 1))
    brand_geometry = scene_document.get("brandGeometryContract")
    if scene_schema_version >= 2:
        if not isinstance(brand_geometry, dict):
            errors.append("scenes-draft.json schemaVersion 2 needs brandGeometryContract")
        else:
            if brand_geometry.get("logoAssetId") != (brand_coverage or {}).get("brandAssetId"):
                errors.append("brandGeometryContract.logoAssetId must match brandCoverage.brandAssetId")
            if brand_geometry.get("logoAxesSealed") is not True:
                errors.append("brandGeometryContract must seal the logo X/Y axes inside the logo component")
            clear_zone = brand_geometry.get("clearZoneRatio")
            if not isinstance(clear_zone, (int, float)) or isinstance(clear_zone, bool) or clear_zone < 0.25:
                errors.append("brandGeometryContract.clearZoneRatio must be at least 0.25")
            narrative_axes = brand_geometry.get("narrativeAxisIds")
            if not isinstance(narrative_axes, list) or any(not isinstance(item, str) or not item.strip() for item in narrative_axes):
                errors.append("brandGeometryContract.narrativeAxisIds must list separate narrative-axis element IDs")
    else:
        warnings.append("legacy scenes draft does not enforce sealed logo axes or a 0.25x clear zone")

    recent_audit = scene_document.get("recentEpisodeAudit")
    brand_reference_counts = None
    if not brand_references_path.is_file():
        errors.append("missing brand-references.json; run deterministic recent-episode discovery before design")
    else:
        try:
            brand_references = json.loads(brand_references_path.read_text(encoding="utf-8"))
            discovered = brand_references.get("availableEpisodeCount")
            copied = brand_references.get("copiedEpisodeCount")
            if not isinstance(discovered, int) or discovered < 0 or copied != min(discovered, 3):
                errors.append("brand-references.json does not contain the bounded latest-three reference pack")
            else:
                brand_reference_counts = (discovered, copied)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid brand-references.json: {exc}")
    if not isinstance(recent_audit, dict):
        errors.append("scenes-draft.json needs structured recentEpisodeAudit")
    else:
        available = recent_audit.get("availableEpisodeCount")
        reviewed = recent_audit.get("reviewedEpisodeCount")
        differences = recent_audit.get("differences")
        if not isinstance(available, int) or available < 0 or not isinstance(reviewed, int) or reviewed < 0:
            errors.append("recentEpisodeAudit counts must be non-negative integers")
        elif reviewed != min(available, 3):
            errors.append("recentEpisodeAudit must review the latest three available episodes")
        if brand_reference_counts and (available, reviewed) != brand_reference_counts:
            errors.append("recentEpisodeAudit counts must match deterministic brand-references.json discovery")
        if available and (not isinstance(differences, list) or not any(isinstance(x, str) and x.strip() for x in differences)):
            errors.append("recentEpisodeAudit needs concrete differences")

    for asset_id in sorted(referenced_assets & ledger.keys()):
        asset = ledger[asset_id]
        asset_type = asset.get("type")
        if asset_type not in ASSET_TYPES:
            errors.append(f"asset {asset_id}: invalid type")
        asset_path = asset.get("path")
        if not isinstance(asset_path, str) or not asset_path.strip() or not local_asset_exists(project, asset_path):
            errors.append(f"asset {asset_id}: path does not resolve inside the project")
        claim_ids = asset.get("claimIds")
        has_claims = isinstance(claim_ids, list) and any(isinstance(item, str) and item.strip() for item in claim_ids)
        has_source = isinstance(asset.get("sourceUrl"), str) and asset["sourceUrl"].strip()
        if asset_type in SOURCE_TYPES:
            parsed = urlparse(asset.get("sourceUrl", ""))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"asset {asset_id}: source-backed type needs a valid sourceUrl")
            if source_visuals is not None:
                source_visual_id = asset.get("sourceVisualId")
                source_visual = source_visuals.get(source_visual_id)
                if source_visual is None:
                    errors.append(f"asset {asset_id}: sourceVisualId must resolve in source-visuals.json")
                elif source_visual.get("usageDecision") != "use":
                    errors.append(f"asset {asset_id}: sourceVisualId is not approved for use")
                elif source_visual.get("localPath") != asset_path:
                    errors.append(f"asset {asset_id}: path differs from shared source visual")
        if asset_type in {"mechanism", "type-data"}:
            if not has_claims:
                errors.append(f"asset {asset_id}: mechanism/type-data needs claimIds")
            else:
                for claim_id in claim_ids:
                    if claim_id not in caption_ids:
                        errors.append(f"asset {asset_id}: claimId {claim_id} is missing from captions.json")

    report = {
        "schemaVersion": 1,
        "status": "ready" if not errors else "failed",
        "project": str(project),
        "sceneCount": len(scenes),
        "visualEngines": sorted(engines),
        "registerSequence": registers,
        "assetCount": len(ledger),
        "typeDataDurationShare": round(type_data_duration / total_duration, 4) if total_duration else None,
        "errors": errors,
        "warnings": warnings,
    }
    output = args.output or project / "video-design-report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
