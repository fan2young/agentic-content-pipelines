# Short-Video Distribution Contract

Read this reference for one shared Douyin and Video Account release. Keep one short-video project, one narration, one locked audio, one caption and timing authority, one encoded `final.mp4`, and one shared cover, publish copy, topic set, and pinned comment. Never create a second render or a platform-specific publishing asset by default.

Design the shared cover and public copy for the intersection of both platforms' visible safe areas and publishing constraints. Use platform-neutral wording and CTA; never say “在抖音” or “在视频号” inside the video or shared copy. If a current platform constraint cannot be satisfied by the shared surface, stop and request an explicit exception instead of silently forking.

Keep only measurement separate: record each platform's retention, traffic, interaction, and follower metrics as platform-tagged snapshots inside the same `short-video/performance-review.json`.

## Format decision

- Default the first six validation episodes to 45–60 seconds; use another duration only when the distribution brief explains why.
- Optimize the opening before shortening the body. A shorter video with the same weak first two seconds does not solve feed rejection.
- Use one test variable per episode. Topic, hook, visual language, duration, voice, and CTA must not all change without recording the confound.

## Required artifacts

Before narration approval, create and approve:

- `distribution-brief.json`: feed entry, viewer decision, format, cover direction, one primary audience action, and the single experiment variable.
- `hook-package.json`: at least three evidence-backed openings and one approved selection.

Before a full render, create and approve `first-five-proof.json` plus its 5–8 second proof clip and sampled frames.

Before final promotion, create schema-version-2 `short-video/release-package.json`, `short-video/cover.png`, `short-video/publish-copy.md`, and `short-video/pinned-comment.md`. The release package contains a `titlePackage` with one recommended distribution title, 2–4 meaningfully different alternatives, and a concise evidence-bound rationale. At final-video handoff, show these titles to the user rather than leaving them buried in a file. After publishing, record `short-video/performance-review.json` at 24 and 72 hours when available.

## Opening contract

- In 0–2 seconds, show the concrete subject plus an abnormal number, consequence, contradiction, object, or decision. Do not begin with a greeting, episode number, slow logo build, or abstract category label.
- By 5 seconds, deliver a bounded payoff, reversal, or explicit promise that the body fulfills.
- Keep the first frame to one dominant idea. Source attribution and the persistent brand bug remain legible but must not compete with it.
- Complete at least two meaningful visual state changes by 5 seconds. A decorative fade, subtitle update, or logo motion alone does not count.
- Review the first-frame and 5-second promise at phone size. Cover strength does not compensate for a weak autoplay opening.

## Cover and feed relationship

The one shared cover and first frame must express the same central conflict but need not be identical. Prefer one dominant claim plus one explanatory limiter. Avoid dense source lines, navigation chrome, and multiple equal-weight cards. Treat platform-generated covers as diagnostic references, not as factual or brand authority.

The recommended distribution title should add a decision-relevant angle rather than merely repeat the cover headline. Alternatives must test genuinely different frames—such as consequence, mechanism, or reader decision—without changing the evidence boundary. Keep all titles platform-neutral.

## Final handoff

When `final.mp4` is promoted, provide in the same response: the recommended title first, the alternatives, the final-video link, and a clickable absolute link to the containing project folder. Then request the separate WeChat branch-start decision defined in `wechat-branch.md`.

## Interaction design

Choose one primary action: `comment`, `follow`, `save`, `share`, or explicitly `none` with a reason.

- Ask for a comment only when the viewer can make a real choice, prediction, or prioritization.
- Ask for a follow only when tied to observable watch signals or a defined follow-up.
- Ask for a save when the video contains a reusable decision rule.
- Ask for a share only when a recipient or practical use is clear.
- Never stack generic requests to like, comment, follow, and share.

Place the interaction trigger where viewers still remain, not only after a long outro. The pinned comment must continue the same decision instead of repeating the caption.

## Performance loop

At 24 and 72 hours, record traffic source, 2-second bounce, 5-second retention, average watch seconds and ratio, completion, engagement, and follower conversion for each platform when available. Tag every snapshot with `douyin` or `video-account`; missing metrics may be `null`, never invented.

Do not fork the next episode from one noisy result. Create separate videos or public assets only after an explicit user decision supported by repeated platform divergence or an irreconcilable publishing constraint.

Compare the result with the project's explicit baseline and hypothesis. Record `keep`, `change`, `stop`, or `wait`, and feed the learning into the next episode's experiment field and recent-episode audit. Early goals are project-specific directional thresholds, not universal platform benchmarks.
