# Next Variable Video Design Contract

Read this before creating or reviewing a video. It is a creative-quality gate, not a fixed template.

## Brand invariants

- Complete the human-approved three-frame direction gate in `visual-direction-proof.json` before authoring full animation. The approved style frames and recent reference pack are creative authorities; lint and encoded QA cannot replace them.
- Preserve the channel core from `visual-direction-lock.md`: warm paper / ink / off-white / signal red as the default balance, an editorial print material language, publication-style Chinese headlines, the complete bilingual lockup in opening plus a later beat, and meaningful red-axis motion. Any deliberate departure must be visible in the three style frames and explicitly approved by the user.
- Show an unobtrusive persistent brand mark in the safe area. It must use an approved project asset, not a generic substitute.
- Reuse the red coordinate axes and origin square as a motion grammar: reveal, measure, route, compare, or verify. Do not use them as inert decoration on every frame.
- Make the brand identifiable in the opening, near the midpoint, and at the close. The outro may enlarge or reconstruct the mark.
- Keep source attribution visible whenever a factual document, screenshot, chart, or quotation is on screen.
- For internal logo animation, inline the SVG and target `#nv-mark`, `#nv-axis-y`, `#nv-axis-x`, and `#nv-origin`. An SVG loaded through `<img>` cannot expose its internal parts to GSAP.
- Copy the project's approved motion-ready logo from its declared asset directory; do not redraw brand geometry per episode.
- Treat the official mark and its internal X/Y axes as one sealed brand component. Never extend `#nv-axis-y` or `#nv-axis-x` beyond the SVG viewBox, scale either axis into a full-frame rule, or connect a scene line to `#nv-origin`.
- Keep a clear zone of at least 0.25× the rendered logo height around the logo bounding box. No narrative rule, axis, connector, crop edge, or generated ornament may enter that zone. A separate scene axis must use its own element/ID, begin outside the clear zone, and must not appear as a collinear continuation of either logo axis.
- For raster covers and generated stills, ImageGen may create only the logo-free background or mechanism art. Composite the supplied official SVG lockup afterward as a deterministic overlay; never ask the model to redraw the NV mark, axes, wordmark, or Chinese/English brand name.

## Episode visual engine

Choose one primary engine and one secondary engine. The engine describes how evidence becomes motion; it is not a style preset.

1. `evidence-documentary`: primary-source pages, screenshots, photographs, annotations, crops, and source trails.
2. `spatial-mechanism`: a process becomes a map, path, queue, gate, field, or transformation in a continuous space.
3. `interface-process`: product or workflow states demonstrate the mechanism through real UI or a restrained reconstruction.
4. `human-work`: hands, workplaces, decisions, consequences, and human review make the affected work tangible.

Do not reuse the same primary engine, layout shell, and transition grammar as the most recent episode. Vary palette balance only inside the channel core unless the user approves a documented departure. Review the latest three episodes from `brand-references.json` and record what changes this time.

## Asset mix

- Build `asset-ledger.json` before composition. Each asset has a unique `id`, a supported `type`, and a project-resolvable `path`. Evidence, photo, footage, and UI assets require a valid `sourceUrl` plus a `sourceVisualId` resolving to a selected entry in the shared `source-visuals.json`; mechanism and type/data assets require `claimIds` that resolve in canonical `captions.json`; brand assets require a real path but no external source. Prefer source-backed screenshots/documents, approved or licensed photography/video, and purpose-built SVG mechanisms. ImageGen fills recorded visual gaps; it does not replace the source-page scan.
- Type and data are accents, not the entire visual world. Allow at most two consecutive pure type/data beats.
- Each factual section needs at least one traceable evidence asset or mechanism visual tied to its source or claim ID.
- Use full-frame crops, spatial continuity, depth, masking, and state changes. Avoid assembling the whole video from cards, grids, and topbar/headline/body shells.

## Motion arc

- Give every logical scene a `build → breathe → resolve` arc and at least one meaningful mid-scene state change. A scene shorter than five seconds may inherit the arc from its containing sequence; do not invent decorative motion just to fill a field.
- Long scenes must not finish their useful motion in the first second. Distribute reveals around the spoken logic.
- Change visual register about every 15–20 seconds in videos longer than 45 seconds: for example document → spatial mechanism → human image → interface.
- Motion should explain causality: the viewer should see what changed, where the bottleneck moved, or how a decision is affected.

For Douyin and Video Account, the first five seconds have a faster contract than the rest of the motion arc:

- Make the first frame legible at phone size and dominated by one claim, object, number, consequence, or decision.
- Show the subject by two seconds and the approved payoff or promise by five seconds.
- Complete at least two meaningful state changes by five seconds. Subtitle changes, fades, and brand-only motion do not count.
- Do not begin with a slow logo build, episode number, abstract category label, or an editorial-slide question with no visible stakes.
- Use the separate `first-five-proof.json` review; the general 10–30 second motion proof does not replace it.

## Relationship grammar and public-surface copy

- Use arrows only for sequence, causality, or directional transfer.
- Use a fork only when outcomes are mutually exclusive or the additive relationship is explicitly labeled. Risk, urgency, testability, and reversibility can coexist; show them as parallel condition-to-rule rows rather than branches.
- Use `+` only for cost or component addition, comparison columns for alternatives, nesting for containment, and a shared axis for repeated measurements.
- Before approval, state each diagram's relationship in one plain sentence. If the sentence does not match the geometry, redesign the geometry.
- Keep production rationale in reports, never in public frames. Reject “原创机制图”, “设计思路”, “安全区”, endpoint/alignment notes, and asset-rights workflow language from titles, captions, footers, SVG text, or HTML.
- Define specialist metrics on first public use. Prefer “95% 请求能在此时间内完成（P95 时延）” before later shortening to “P95 时延”.

## Required scene metadata

Add these fields to every item in `scenes-draft.json` before rendering:

- `visualEngine`: one of the four engines above.
- `visualRegister`: `evidence`, `mechanism`, `interface`, `human`, or `type-data`.
- `midSceneChange`: a concrete visual state change, not “elements animate in”.
- `brandIntegration`: how the NV axis, origin, mark, or source signature participates.
- `assetIds`: source or approved-asset identifiers used by the scene.

At the `scenes-draft.json` document root, use `schemaVersion: 2` and add structured `brandCoverage` with opening/midpoint/close scene IDs and a brand asset ID. Also add `brandGeometryContract` with the same `logoAssetId`, `logoAxesSealed: true`, `clearZoneRatio: 0.25` or greater, and the IDs of every separate narrative axis. Add `recentEpisodeAudit` whose counts exactly match deterministic `brand-references.json`; never self-report zero when discovery found prior episodes. Do not add editable scene times or `compositionDuration` here. Read all scene starts, ends, and composition duration from canonical `timing.json`; its ranges must start at zero, remain ordered and non-overlapping, avoid unexplained gaps over 0.5 seconds, match scene order exactly, and end at `compositionDuration`. The secondary visual engine must occupy at least 10% of the running time.

The validator rejects empty scene lists, broken canonical timing, invalid asset types/paths/claims, missing or token primary/secondary engines, and type/data occupying more than 40% of a video longer than 15 seconds. Heading wording in `DESIGN.md` is advisory; structured visual metadata in scenes and canonical time in `timing.json` are authoritative. This is a structural preflight only: repeated cards, slide-like cuts, and visual sameness remain rejection conditions in encoded-frame visual QA.

## Rejection conditions

Reject the composition before full rendering if any is true:

- No persistent, legible Next Variable brand marker.
- No user-approved three-frame visual direction, or a finished composition that materially departs from the approved style frames.
- More than two consecutive pure type/data beats.
- A factual section has no traceable evidence or mechanism visual.
- A long scene becomes static after its entrance animation.
- The frame is dominated by repeated cards, identical scene shells, or slide-like page changes.
- The latest-three-episode audit is absent when prior episodes are available.
- A connector implies a relationship the underlying conditions do not have.
- Internal production language is visible on the public surface.
- The logo's internal axis is extended, touched, or visually merged with a narrative axis, rule, connector, or crop edge.
- A short-video opening fails phone-size review, hides the subject beyond two seconds, delays its payoff beyond five seconds, or relies on a cover to compensate for weak autoplay frames.

Run `scripts/validate_video_design.py PROJECT_DIR --output PROJECT_DIR/video-design-report.json`. Fix errors; review warnings in context rather than mechanically suppressing them. Before delivery, run `scripts/validate_publish_surface.py` on reader-facing HTML and SVG inputs; raster and encoded frames still require visual review.
