# Backend Implementation Plan

Owner: Ruthvik  
Maintained by: Ruthvik and Codex  
Last updated: October 28, 2026  
Status: Phase 0 through Phase 3 complete; Phase 5 hardening in progress

This is the working plan for Ruthvik's backend work. It uses simple language so
that teammates and coding assistants can quickly understand what we are doing.
It describes what we plan to build. It is not the record of completed work.

The larger team schedule remains in [`PLAN.md`](../PLAN.md). This document is
only about turning Ruthvik's backend plan into working code.

## 1. The problem

The engine receives:

- a finished design with text, images, and shapes;
- the size of a new canvas.

It must return the same design elements arranged for the new canvas. It must
move and reflow the elements. It must not stretch the whole design like a
picture.

Stage 1 is a headless Python engine. It does not need a web page or an Adobe
Express add-on. The official brief says the Express add-on is finale work.

## 2. Rules we cannot break

- Return every original element ID exactly once.
- Do not add or remove elements.
- Keep element types, image assets, text content, and font families unchanged.
- Never generate, redraw, or edit image pixels.
- Keep normal images in proportion. A `cover` background may crop.
- Keep every output element inside the target canvas. Repair decorative bleed
  unless Adobe gives a newer written exception.
- Preserve groups, stacking order, brand colors, and the visual hierarchy.
- The engine must work offline in the submitted Docker container.
- Do not write rules for one sample, filename, brand, or element ID.
- The returned object must contain only `canvas` and `elements`.

## 3. Planned engine flow

```text
source design
  -> validate the input
  -> measure the layout
  -> choose useful layout strategies
  -> build several complete candidates
  -> repair each candidate
  -> reject candidates that break hard rules
  -> score the remaining candidates
  -> return the best candidate
  -> use a safe fallback if every candidate fails
```

## 4. Work phases

### Phase 0 - Make the development loop reliable

Status: Complete

- Install the existing runtime dependencies.
- Run all three starter samples with the real renderer.
- Save the current stretched output only as a local comparison.
- Pin `cr-renderer` to a tested commit before release.

Done when: `python -m engine.main` creates real JSON and PNG output for all
three samples.

### Phase 1 - Hard validation and geometry

Status: Complete

Planned files:

- `engine/geometry.py`
- `engine/constraints.py`
- `tests/test_geometry.py`
- `tests/test_constraints.py`

Build small helpers for:

- boxes, centers, edges, and aspect ratios;
- rotated bounds;
- proportional scaling;
- moving an element or a whole group;
- overlap and spacing measurements;
- keeping boxes inside the canvas;
- checking exact IDs and protected fields.

Done when: tests catch duplicate IDs, missing IDs, changed text/assets/fonts,
image distortion, rotated overflow, invalid sizes, and input mutation.

### Phase 2 - Safe baseline and candidate layouts

Status: Complete

Planned files:

- `engine/layouts.py`
- `engine/resize.py`
- `tests/test_resize.py`

Start with these general strategies:

1. `preserve_and_repair`: proportional scale, center, then repair bounds.
2. `vertical_stack`: useful for tall canvases.
3. `horizontal_split`: useful for wide canvases.
4. `compact_banner`: useful for very short, wide canvases.

Groups such as a button shape and its label must move together. Background
images use `cover`. Other images keep their source proportion.

Done when: Level 1 and Level 2 look clearly better than the stretch baseline,
and Level 3 returns a complete legal design.

### Phase 3 - Repair and scoring

Status: Complete

Score only candidates that pass hard validation. Use simple penalties for:

- accidental overlap;
- text with too little space;
- poor alignment;
- uneven spacing;
- broken groups;
- lost visual hierarchy;
- crowded canvas edges.

Do not punish expected overlap between members of the same group, a background,
or clearly layered decoration.

Done when: the scorer consistently prefers the better legal candidate in
small controlled tests.

### Phase 4 - Optional local decision model

Status: Blocked by official model details and core-engine progress

Reem's local policy may suggest which strategies to try and how to weight the
score. Ruthvik's engine must still work when that module is missing or fails.

Do not ship model weights until Adobe confirms the approved-model list and size
limit. A transparent rule-based policy is an acceptable fallback.

### Phase 5 - Hardening and release

Status: In progress

- Add varied synthetic fixtures, not just the three samples.
- Check deterministic output by running the same input more than once.
- Inspect every real PNG, not only JSON.
- Build and run `linux/amd64` Docker with `--network none`.
- Test from a clean clone.
- Update the root README with the final approach and exact commands.

Completed so far: synthetic structural stress tests, repeat determinism, a
clean `linux/amd64` build, and a network-disabled read-only container run.
Remaining: clean-clone rehearsal and broader rendered visual-quality fixtures.

## 5. Research ideas we will use

From LayoutGAN:

- treat the layout as a set of elements, not a special fixed order;
- measure relationships between pairs of elements;
- use alignment, overlap, spacing, and boundary information;
- start from a transformed layout and repair it instead of generating a new
  design from nothing.

From seam carving:

- give elements and groups an importance score;
- make expensive changes to important content less often;
- measure the total damage caused by a layout change;
- use a safe fallback when no low-damage layout exists.

We will not use pixel seam carving. Editing or removing image pixels would
break the challenge rules.

## 6. Current priority

The remaining order is:

1. varied fixtures and stronger repair;
2. offline Docker reliability;
3. optional decision-model integration after its contract is agreed;
4. UI or extra polish.

## 7. Questions still open

- What are the final approved-model list and model-size limit?
- What are the exact CPU, RAM, and disk limits of the M5 Pro evaluator?
- Does Adobe have any newer written exception to the strict on-canvas rule?
  Until then, clamp or repair decorative bleed.
- Should the tested `cr-renderer` pin change before the final submission?
- What are the official submission date, code-freeze date, and finale dates?

The dates in the team `PLAN.md` are not stated in the official final brief, so
they need separate organizer confirmation. These questions do not block Phases
0 through 3.

## 8. How to update this document

- Codex changes a phase status when implementation starts or finishes.
- Codex updates this plan only when the planned approach or work order changes.
- Record important choices in [`DESIGN_DECISIONS.md`](DESIGN_DECISIONS.md).
- Record completed work and test results in
  [`IMPLEMENTATION_LOG.md`](IMPLEMENTATION_LOG.md).
- Keep the short team summary in [`RUTHVIK_HANDOFF.md`](RUTHVIK_HANDOFF.md).
