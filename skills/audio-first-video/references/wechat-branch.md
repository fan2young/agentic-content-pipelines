# Optional post-final article handoff

Use this only after `video_final` is `approved`. The video final lock does not authorize WeChat production.

## Start checkpoint

Ask whether the user wants to start a separate article-production task. Video approval does not authorize that work.

After an explicit yes, create the context firewall:

```bash
python3 /path/to/article-adapter/build_article_request.py --project <project-dir>
```

The request may point only to `editorial-brief.json`, `sources.md`, and `article.md`. It must not include narration, scenes, audio, captions, video design, renders, review history, or conversation excerpts.

## Handoff boundary

Return the absolute path to `article-request.json`. Continue in a fresh task using an explicitly installed article adapter. This repository does not bundle or silently install one.

Do not read GZH component libraries, source visuals, or article assets here. Do not call `activate_wechat_branch.py`; retain it only for legacy packages created before this context-isolation rule. The fresh article task owns titles, layout, cover, inline images, public-surface validation, and its own `article-handoff.json`.
