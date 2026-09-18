# Editorial topic gate

Use this gate before initializing a production project. The maintainer may use any editorial research process, but the resulting brief must pass the included validator before production begins.

## Discovery boundary

- Use rankings and trend lists only to discover leads.
- Scan all three lanes on each run: `ai`, `business`, and `career`.
- Build at least three candidates across at least two lanes. If a lane yields no credible candidate, record the reason in `laneGapReasons`.
- Record `retrievedAt` and a `deduplicationNote` describing how repeated reports of the same event were collapsed.
- For every candidate record `firstPublicAt`, `meaningfulUpdateAt`, `saturationRisk`, and `incrementalValue`.
- Do not let market price, company valuation, earnings, or macro data dominate merely because they are easy to quantify.
- Prefer a lower-heat candidate when it offers a clearer changed variable, transmission mechanism, reader decision, and evidence base.
- For a Douyin or Video Account candidate, record the current public conversation, freshness window, search intent, and one evidence-backed visual anchor in the later distribution brief. These affect entry timing and packaging, never the brand-fit threshold or fact boundary.

## Five-variable test

The selected candidate must answer yes to all five questions:

1. Is there a verified new fact?
2. Is there a visible mechanism rather than coincidence?
3. Does it change a company, industry, job, or personal choice?
4. Is there enough public evidence for the central judgment?
5. Will the target reader leave with a clearer judgment?

Score `brandFitScore` from 0 to 5. Production requires at least 4. `heatScore` is contextual and has no minimum.

A story that was already broadly reported is not made fresh by a minor restatement. A selected candidate with `saturationRisk: high` fails the gate. A later update qualifies only when it changes the mechanism, affected choice, evidence boundary, or watch signals, and `incrementalValue` names what this edition adds.

## Decision boundary

Use `decision: publish` only when the selected candidate passes the five-variable test, has at least three evidence points, and includes at least two observable watch signals. Otherwise use `decision: no-publish`, explain why, and stop before production.

## Editorial brief

Create `editorial-brief.json` against `schemas/editorial-brief.schema.json`. Keep it concise and attributable. Required content:

- discovery date/source/retrieval time, deduplication note, and scanned lanes;
- candidate pool with lane, first exposure, meaningful update, saturation risk, incremental value, variable thesis, scores, evidence count, and five test results;
- selected candidate, primary column, content type, target reader, and reader decision;
- 3–5 evidence points with direct URLs and dates;
- mechanism, impact map, uncertainty, and 2–3 watch signals;
- explicit `publish` or `no-publish` decision and approval metadata.

The brief is the editorial contract. Article and narration may refine wording but must not silently change its central variable, audience, or decision. If those change, revise and reapprove the brief first.

## Mix review

Topic quality is evaluated per item; lane balance is evaluated over time. At the end of each publishing week, inspect the published primary columns and note sustained overconcentration. Do not use a quota to force a weak daily topic, but do widen the next discovery scan when one lane has dominated.
