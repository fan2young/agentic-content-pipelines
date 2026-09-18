# Source Visual Contract

Create `source-visuals.json` while building `sources.md`, before any channel-specific visual work.

## Scan and selection order

1. Inspect each primary source for charts, diagrams, UI screenshots, photographs, footage, and document excerpts that directly support a claim.
2. Download approved candidates into project-local `assets/source/`; never hotlink production media.
3. Prefer official evidence visuals, then clearly licensed media, then purpose-built mechanism graphics.
4. Use ImageGen only when the ledger records a real visual gap that source material cannot explain.
5. Reuse the same decided local asset across video and WeChat instead of researching or downloading it twice.

## Rights and context

A public page is not blanket permission to reuse every image on it. Record the owner, source page, original asset URL, usage basis, attribution, and any license evidence. An image embedded from a third party requires independent rights evidence. `official-editorial-quotation` documents an editorial rationale; it is not a legal guarantee.

For a selected crop, preserve the evidence context: axes, legend, date, source mark, meaningful labels, and surrounding UI or document cues. Never crop a chart or screenshot into a stronger claim than the source supports. Unknown or prohibited rights cannot enter production.

## Validation

```bash
python3 scripts/validate_source_visuals.py project/source-visuals.json --require-decided
```

Keep full raw source URLs in attribution surfaces. Do not replace them with generic anchor labels.
