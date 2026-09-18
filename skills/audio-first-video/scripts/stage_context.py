"""Context groups for bounded video-production tasks."""

CONTEXTS = ("content", "audio_timing", "visual_release", "article_external")

STAGE_CONTEXT = {
    "editorial_brief": "content",
    "sources": "content",
    "distribution_strategy": "content",
    "hook_selection": "content",
    "article": "content",
    "narration": "content",
    "audio_lock": "audio_timing",
    "alignment": "audio_timing",
    "timing": "audio_timing",
    "visual_direction": "visual_release",
    "runtime_preflight": "visual_release",
    "first_five_proof": "visual_release",
    "video_review": "visual_release",
    "distribution_package": "visual_release",
    "video_final": "visual_release",
    "performance_review": "visual_release",
    "wechat": "article_external",
}


def context_for_stage(stage: str) -> str:
    return STAGE_CONTEXT.get(stage, "visual_release")
