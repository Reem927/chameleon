# Ruthvik Backend Handoff

Last updated: October 30, 2026  
Branch: `feature/ruthvik-research-quality`  
Current backend status: engine, cleanup pass, decision policy, ranking and demo API complete; release check (Docker offline, clean clone, README) next

This is the short document Ruthvik can share with teammates and their coding
assistants. Read this before changing or integrating backend code.

Codex will refresh this file after meaningful backend progress or an interface
change that affects Reem or Shivraj.

## What Ruthvik owns

Ruthvik is responsible for:

- the official `resize(source, target_canvas)` engine;
- geometry, groups, candidate layouts, cleanup, scoring, and final validation;
- the decision policy, ranking and demo API, taken over from Reem with the team's agreement;
- backend tests;
- the root Dockerfile, runtime requirements, and final engine README;
- making sure the scored engine runs offline without the API or frontend.

See [`PLAN.md`](../PLAN.md) for the team plan.

## Current state

- `engine/resize.py`: decision policy -> candidate layouts -> hard-rule check -> ranking -> safe fallback; never raises.
- `engine/layouts.py` builds `preserve_and_repair` plus row, column and two-row flow layouts at three graphic ratios.
  Full-canvas plain rectangles fill the target like a cover image, and a snug card behind text moves with that text.
  Same-ratio targets keep the original design.
- `engine/rectify.py` is a cleanup pass (after LayoutRectifier): it snaps drifted alignments and moves things out of new overlaps.
  Each cleaned layout is a separate `+clean` candidate, so it can never make a result worse.
- The score has eleven parts: collision, text, hierarchy, canvas use, alignment, balance and spacing, group cohesion, plus reading order, similarity to the source, source alignments kept, and area share (from LayoutGAN and LayoutRectifier).
  The "looks like the original" parts count only as far as the target shape allows and only for text that stays readable.
- `engine/decision_policy.py` is a small set of rules, not a trained model; see [`model-notes.md`](model-notes.md).
  Today one rule adds two-column and three-row layouts for designs with 8 or more units.
- `engine/ranking.py` picks the best legal candidate and builds the diagnostics the API returns.
- Smallest text on the official samples: 37.3px (Level 1), 15.3px (Level 2), 7px (Level 3).
- Tests: 117 pass. Fixture report over 13 designs x 11 sizes (143 cases): 0 invalid, 0 overflowing, 3 with new overlaps, 2 with text below 4px.
- Not yet re-run on this branch: the `linux/amd64` Docker build with `--network none` and a clean clone. They passed on October 28 for the earlier engine.
- Known limits: dense designs at 320x50 still get text below 4px; small logos become tiny in extreme banners.

## Demo API (for Shivraj)

- Run `.venv/bin/python -m api.app` (port 8000), then `cd frontend && npm run dev`.
- The UI finds `frontend/src/services/index.ts` automatically and resizes live to any size.
- The contract, including `DebugPayload`, is [`api-contract.md`](api-contract.md).
  The score breakdown has eleven parts, not seven.
- The API uses only the standard library, binds to localhost, and is not in the Docker image.
  `engine/` never imports `api/` or `frontend/`.

## Hard rules for every contributor and coding assistant

- Read `RULES.md`, the schema, `PLAN.md`, and this handoff first.
- Preserve exact IDs, types, assets, text, fonts, groups, and stacking intent.
- Never generate or edit image pixels.
- Never hardcode a sample filename, element ID, or brand name.
- Do not edit another owner's files without approval.
- Do not edit the official samples, schema, brand kit, or renderer.
- Do not add cloud calls or runtime downloads.
- Do not return debug fields from `resize()`.
- Record decisions and completed work in the matching docs.
- Include exact tests and results in every handoff.

## What the research contributes

- LayoutGAN and Attribute-conditioned LayoutGAN: reading order and area share in the score.
- LayoutRectifier: parent/child overlap, keeping the source's alignments, similarity, and the cleanup pass.
- ORC Layout: the policy adds weighted options and never removes one; balanced rows for dense designs.
- Seam carving: importance thinking only.

No model is trained and no pixels are edited.

## Current requests for teammates

From Reem:

- review `engine/decision_policy.py`, `engine/ranking.py` and `api/`, which Ruthvik built in your lane.

From Shivraj:

- try the live UI against the API;
- update the inspector for the eleven-part breakdown in `api-contract.md`.

From everyone:

- announce pushed branches and interface changes before integration;
- resolve conflicts through the file owner, then rerun tests.

## Open questions

- Adobe's final approved-model list and model-size limit.
- Exact evaluator CPU, RAM, and disk limits.
- Whether Adobe publishes a newer exception to strict on-canvas output. Until
  then, decorative bleed will be repaired.
- Whether the tested `cr-renderer` pin should change before release.
- Official submission, code-freeze, and finale dates. The dates in `PLAN.md`
  are not present in the final challenge brief.

## Where to look next

- Team plan and file ownership: [`PLAN.md`](../PLAN.md)
- Engine overview and run commands: [`README.md`](../README.md)
- Detailed backend plan, decision log, and implementation log are kept locally by Ruthvik.
  Ask Ruthvik if you need a specific decision or test record.
