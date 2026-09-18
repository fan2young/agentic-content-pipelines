# Original Spoken-Script Design

Use this reference to convert a source-backed article or research memo into an original Chinese narration. The goal is attention plus comprehension, not imitation of a named creator.

## Choose a mode

- `reporting`: Lead with the strongest verified change, explain context and implications, and end on the unresolved variable. Use for sensitive or evidence-thin news.
- `explainer`: Open with a concrete tension, state what the viewer will understand, move through evidence-led beats, introduce a real turn or counterargument, and synthesize. Default for finance and technology analysis.
- `review`: Start from the audience's decision, define evaluation dimensions, present evidence and trade-offs, then give a bounded verdict.

Do not use travel-vlog, host banter, sponsor integration, or creator-persona patterns unless the user's project actually needs them.

## Build the argument

For an explainer, use this flexible sequence:

1. **Hook:** One concrete contradiction, consequence, scene, object, or audience decision. Avoid generic greetings and unsupported shock.
2. **Promise:** State the larger question and, when useful, the two or three issues the narration will resolve.
3. **Evidence-led beats:** Give each beat one job. Prefer `claim → evidence → plain-language explanation → consequence`.
4. **Turn:** Add a genuine constraint, counterargument, or change in interpretation. Do not insert “但是” merely to satisfy a template.
5. **Synthesis:** Return to the opening tension and state what changed, what did not, and what to watch next.
6. **Audience action:** Make a channel-appropriate engagement decision. For short-video platforms, choose one primary action or explicitly record `none` with a reason. Never force a copied sign-off or stack generic requests.

The sequence may contract for a short video or expand for a long one. Do not force seven sections when the argument has three.

## Adapt for short-video feeds

Read `short-video-distribution.md` for Douyin or Video Account and approve `distribution-brief.json` plus `hook-package.json` before approving the narration.

- Use 0–2 seconds to identify the subject and concrete tension; use 2–5 seconds to deliver a bounded payoff, reversal, or promise.
- Do not spend the opening on greetings, source credentials, episode setup, or an abstract question whose stakes are not visible.
- Default the first six validation episodes to 45–60 seconds. Compress evidence into one mechanism and one consequence instead of reading a shortened article.
- Place the primary interaction trigger before a long outro. Tie comments to a real choice, follows to observable watch signals, saves to a reusable rule, and shares to a named use or recipient.
- Write the cover, first frame, spoken hook, and body promise as one system. Each may use different wording, but they must make the same claim within the same evidence boundary.

## Use retention devices selectively

- Address “你” when it clarifies the viewer's stake; do not maintain an artificial quota.
- Ask a question only when the following passage answers or productively complicates it.
- Convert a number into a familiar scale only when the comparison is valid, sourced, and more informative than the original unit.
- Use an analogy to explain mechanism, not to prove a claim.
- Prefer short spoken sentences around dense names or figures, but preserve necessary qualifications.
- Use one memorable line only if it follows from the evidence. Do not manufacture a slogan as a mandatory ending.

## Preserve the fact boundary

Keep `article.md` as the fact master. For every narration beat, be able to identify its source paragraph or source link. Mark unresolved gaps as `[待核实：…]`; do not record TTS while placeholders remain.

Do not turn correlation into causation, market interpretation into fact, a broad financial metric into a narrower one, or uncertainty into confidence. Sponsor claims require user-supplied substantiation and explicit approval.

## Write for speech and TTS

- Read names, tickers, abbreviations, dates, percentages, currencies, and units aloud.
- Create a pronunciation-safe version only after approval; record every changed spelling.
- Use punctuation to express breathing and emphasis, not article typography.
- Estimate duration provisionally, then calibrate with the selected human voice or TTS candidate. The locked audio remains the timing authority.

## Review before audio generation

Confirm:

- The hook is true and fulfilled by the body.
- Every unfamiliar company, organization, product, or person is explained in plain language at first meaningful mention, and the relationship between the main subjects is clear.
- The core mechanism can be restated in one or two plain-language sentences without relying on unexplained shorthand.
- Each beat advances the thesis and contains sufficient evidence.
- Retention devices do not crowd out explanation.
- The draft does not reproduce a creator's signature wording, persona, or fixed ending.
- The spoken version preserves the article's qualifications and source boundary.
- The user has approved both the exact words and any pronunciation-safe substitutions.
- For Douyin and Video Account, record the provisional character count, estimated speaking duration, and comparison with the approved target duration before content lock. If it falls outside the permitted range, shorten it or obtain the explicit project-level duration exception before approval—not after rendering.
- For Douyin and Video Account, the selected hook, five-second payoff, one primary audience action, and target duration match the approved distribution brief.

## Provenance

The structural analysis was informed by the MIT-licensed `imfangli/mediastorm-copywriter` repository at commit `1d91abdff0b1bf0dfef8d6c73e0970ed39ae6403`. This adaptation retains general craft principles only. Do not reproduce its example sentences, creator-specific persona, or signature CTA.
