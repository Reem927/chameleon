# Ruthvik Backend Handoff

Last updated: October 28, 2026  
Branch: `feature/ruthvik-core-engine`  
Current backend status: Phase 0 through Phase 3 complete; Phase 5 in progress (readability and hardening done, clean-clone rehearsal pending)

This is the short document Ruthvik can share with teammates and their coding
assistants. Read this before changing or integrating backend code.

Codex will refresh this file after meaningful backend progress or an interface
change that affects Reem or Shivraj.

## What Ruthvik owns

Ruthvik is responsible for:

- the official `resize(source, target_canvas)` engine;
- geometry, groups, candidate layouts, repair, and final validation;
- backend tests;
- the root Dockerfile, runtime requirements, and final engine README;
- making sure the scored engine runs offline without the API or frontend.

See [`PLAN.md`](../PLAN.md) for the complete team file-ownership rules.

## Current state

- `engine/geometry.py` provides rotation-aware bounds, proportional scale, overlap, group movement, and canvas clamping.
- `engine/constraints.py` rejects candidates that break hard rules.
- `engine/text_fit.py` measures brand fonts the way the renderer wraps them and fits text to a box.
  Widths match the Linux Docker renderer to the pixel and never fall below the macOS renderer.
- `engine/layouts.py` builds ten deterministic candidates: `preserve_and_repair` plus row, column, and two-row flow layouts, each with graphics at 100%, 60%, and 30% of the text scale.
  Lone text reflows into its slot, all text shares one scale, and text stays at 7px or more when the layout allows.
- `engine/resize.py` rejects illegal candidates, returns the highest-scoring legal one, and never raises.
- The score measures accidental overlap, text readability (weighted by source prominence plus the worst text), hierarchy, canvas use, alignment, spacing, and group cohesion.
- On the official samples, the smallest text is now 37.3px (Level 1), 15.3px (Level 2), and 7px (Level 3).
  Before this work, Level 2 text went down to 7.6px and Level 3 text to 1.5px.
- 57 tests pass locally and inside the `linux/amd64` image.
- The image runs all samples with `--network none` and a read-only filesystem, and all outputs validate.
- Known limits: very small targets with many elements (for example Level 3 at 320x50) still produce unreadable text, and the Level 3 logo becomes very small in the extreme banner.

## Backend direction

Ruthvik's engine will:

1. validate the input and protected fields;
2. measure elements and groups;
3. generate several complete deterministic layouts;
4. repair bounds, spacing, text size, and group placement;
5. reject illegal layouts;
6. rank legal layouts;
7. return the best result or a safe fallback.

The first strategies will be preserve-and-repair, vertical stack, horizontal
split, and compact banner.

## Contract with Reem

Reem's decision component may suggest policies and rank candidates. It must be
local, deterministic for the same input, and optional from Ruthvik's point of
view.

Expected direction:

```python
suggest_policies(source, target_canvas) -> list[dict]
rank_candidates(source, target_canvas, candidates) -> tuple[dict, dict]
```

Ruthvik generates complete candidates and performs final validation. Debug
metadata must not be added to the official output.

Before either side implements this integration, both owners should confirm the
exact policy keys and candidate expectations in a small contract document or
shared PR.

## Contract with Shivraj

The Stage 1 engine has no frontend dependency. Shivraj's UI or Reem's local API
may call the engine, but `engine/` must never import from `api/` or `frontend/`.

The official final brief says the Express add-on is finale work. A development
UI is helpful but must not delay the scored engine.

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

- LayoutGAN: set-based element relationships, alignment, overlap, wireframe
  boundaries, and transform-then-repair thinking.
- Seam carving: importance scores and minimum-damage changes at the element or
  group level.

Do not copy either paper directly. Do not train LayoutGAN for the current
deadline, and do not use pixel seam carving.

## Current requests for teammates

From Reem:

- confirm the smallest policy dictionary needed for first integration;
- keep the model optional and provide deterministic behavior;
- share any planned scorer features before they become fixed interfaces.

From Shivraj:

- keep the UI/API contract separate from the official engine output;
- do not require Node, a server, or a browser inside the scored container.

From everyone:

- announce pushed branches and interface changes before integration;
- avoid editing Ruthvik-owned engine files in parallel;
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
