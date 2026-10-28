# Ruthvik Backend Handoff

Last updated: October 28, 2026  
Branch: `main` at review time  
Current backend status: Phase 0 through Phase 3 complete; Phase 5 in progress

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

- `engine/geometry.py` now provides rotation-aware bounds, proportional scale,
  overlap, group movement, and canvas clamping.
- `engine/constraints.py` now rejects candidates that break hard rules.
- `engine/layouts.py` now generates four deterministic group-aware layouts.
- `engine/resize.py` now rejects illegal candidates, scores every legal
  candidate, selects the highest score, and has a safe proportional fallback.
- The fallback score measures overlap, text readability, hierarchy, canvas
  use, alignment, spacing, and group cohesion.
- The real renderer works locally, and its dependency is pinned to a tested
  commit.
- There are 42 passing geometry, constraint, renderer, resize, scoring, and
  synthetic hardening
  tests.
- All three official samples pass hard validation and render without engine
  errors.
- Stronger repair, varied fixtures, and offline Docker verification are the
  next work.
- The `linux/amd64` image builds and completes all samples with networking and
  the container filesystem disabled for writes. All container outputs validate.
- The three team members are working separately and have not pushed their
  implementation branches yet.

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

- Read `RULES.md`, the schema, `PLAN.md`, and these four docs first.
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

- Work to do: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
- Reasons behind choices: [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md)
- Work already completed: [`IMPLEMENTATION_LOG.md`](IMPLEMENTATION_LOG.md)
