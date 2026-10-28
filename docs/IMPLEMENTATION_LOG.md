# Backend Implementation Log

Owner: Ruthvik  
Maintained by: Codex after each implementation task  
Last updated: October 28, 2026

This file records what was actually implemented. It lets us compare the working
code with [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

Use one entry per completed task. Say what changed, why it changed, and what was
tested. Never write that a test passed unless it was actually run.

Codex will add or update an entry after every completed, partial, or blocked
implementation task. Each entry will compare the result with the implementation
plan so Ruthvik can see what changed from the original idea.

## Entry template

```text
## YYYY-MM-DD - Task title
Plan item:
Status: Complete / Partial / Blocked
Files changed:
What we implemented:
How it works in simple terms:
What is different from the plan:
Tests run and results:
Rendered output checked:
Known limits:
Next step:
```

## 2026-10-28 - Repository review and documentation setup

Plan item: Preparation before Phase 0  
Status: Complete

Files changed:

- `.gitignore`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DESIGN_DECISIONS.md`
- `docs/IMPLEMENTATION_LOG.md`
- `docs/RUTHVIK_HANDOFF.md`

What we implemented:

- Reviewed the starter engine, plan, rules, schema, samples, and renderer.
- Reviewed the official challenge brief.
- Reviewed LayoutGAN and seam-carving research for useful concepts.
- Added four living project documents.
- Changed `.gitignore` so local PDFs remain ignored while Markdown documents
  can be committed.

How it works in simple terms: The repository now has one place for upcoming
work, one for reasons behind choices, one for completed work, and one short
handoff for teammates.

What is different from the plan: No backend feature has been implemented yet.
The code is still the starter's stretch baseline.

Tests run and results:

- `python3 -m compileall -q engine renderer`: passed.
- `python3 -m engine.main`: stopped because Pillow is not installed in the
  current local environment.
- Direct baseline geometry check: every sample distorted at least one normal
  image beyond the approximate 5% tolerance.

Rendered output checked: No. The real rendering dependencies must be installed
first.

Known limits:

- Geometry, constraints, layouts, ranking, and backend tests do not exist yet.
- Final model limits and complete evaluator hardware details are still open.

Next step: Complete Phase 0, then build hard validation and geometry tests.

## 2026-10-28 - Complete Phase 0 and Phase 1 foundation

Plan item: Phase 0 - development loop; Phase 1 - validation and geometry  
Status: Complete

Files changed:

- `requirements.txt`
- `engine/geometry.py`
- `engine/constraints.py`
- `tests/test_geometry.py`
- `tests/test_constraints.py`
- `tests/test_renderer.py`
- backend planning and handoff documents

What we implemented:

- Created a local `.venv` and installed the existing project dependencies.
- Pinned `cr-renderer` to tested commit
  `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`.
- Verified the real renderer on all three starter samples.
- Added rotation-aware bounds, overlap, proportional scaling, translation,
  shared group movement, and safe canvas clamping.
- Added hard candidate validation for exact IDs and counts, exact target canvas,
  protected fields, finite numbers, type fields, rotated bounds, and image
  proportions.
- Added standard-library unit tests and real-renderer integration tests.

How it works in simple terms: Geometry helpers tell us where an element is
really visible, even when it is rotated. The validator acts as a safety gate.
It returns a list of exact problems and does not allow an unsafe layout to be
treated as a valid candidate.

What is different from the plan:

- Phase 0 and Phase 1 were completed together instead of separately.
- We used standard-library validation rather than adding a JSON-schema package.
- We added two renderer integration tests so a fake fallback preview cannot be
  mistaken for a successful real render.
- Candidate layouts are still intentionally deferred to Phase 2.

Tests run and results:

- `.venv/bin/python -m unittest discover -s tests -v`: 27 tests passed.
- `python3 -m compileall -q engine tests`: passed.
- `.venv/bin/python -m engine.main`: processed and rendered all three samples.
- `git diff --check`: passed.

Rendered output checked: Yes. All PNG sizes matched their target canvases. The
visual inspection confirmed that the current stretch baseline is not usable.
The Level 3 missing holiday asset produced the expected placeholder warning and
did not crash.

Baseline validator results:

- Level 1: one image-ratio violation.
- Level 2: one off-canvas element and two image-ratio violations.
- Level 3: two rotated off-canvas elements and three image-ratio violations.

Known limits:

- `resize()` still uses the old stretch baseline; the new validator is not yet
  connected to candidate selection.
- Local verification used Python 3.14. The release container uses Python 3.11
  and will be tested during Docker hardening.
- The validator protects rotation instead of allowing strategies to change it.

Next step: Start Phase 2 with a safe preserve-and-repair candidate, then add
vertical, horizontal, and compact-banner strategies.

## 2026-10-28 - Complete Phase 2 candidate layouts

Plan item: Phase 2 - safe baseline and candidate layouts  
Status: Complete

Files changed:

- `engine/layouts.py`
- `engine/resize.py`
- `tests/test_resize.py`
- `README.md`
- backend planning, decision, implementation, and handoff documents

What we implemented:

- Replaced the independent X/Y stretch baseline.
- Added preserve-and-repair, vertical-stack, horizontal-split, and
  compact-banner candidates.
- Added general strategy selection based on source and target shape.
- Kept `group_id` members together through one shared scale and translation.
- Detected full-canvas cover backgrounds without using element IDs.
- Kept ungrouped shapes as separately positioned decoration.
- Connected hard validation to candidate selection.
- Added a deterministic proportional fallback.

How it works in simple terms: The engine now looks at the new canvas shape and
chooses a matching way to arrange the design. It moves whole groups together,
keeps normal images proportional, fills the canvas with the background, and
returns only a layout that passes the Phase 1 safety gate.

What is different from the plan:

- Phase 2 uses a small shape-based chooser because Phase 3 scoring is not ready.
- Horizontal and vertical strategies currently use equal grid cells. This is
  deliberately simple and will be improved by Phase 3 scoring and repair.
- Decorative ungrouped shapes are positioned separately from content units.

Tests run and results:

- `.venv/bin/python -m unittest discover -s tests -v`: 33 tests passed.
- `.venv/bin/python -m compileall -q engine tests`: passed.
- `.venv/bin/python -m engine.main`: all three samples completed with no
  self-check warnings.
- Hard candidate validation: all three outputs returned zero problems.
- `git diff --check`: passed.

Rendered output checked: Yes. Level 1 is proportional and centered. Level 2 is
reflowed into a clean horizontal sequence. Level 3 uses a complete two-row
banner layout and shows the expected missing-asset placeholder.

Known limits:

- The engine does not compare visual scores yet; it uses target-shape rules.
- Text fitting uses uniform font scaling and does not measure final text-box
  capacity during candidate generation.
- Level 3 is legal and organized, but some text is necessarily very small in a
  728x90 canvas containing 17 elements.
- Ungrouped shapes are assumed to be decoration in the current strategies.

Next step: Phase 3 will score legal candidates using overlap, alignment,
spacing, text capacity, hierarchy, and group cohesion.

## 2026-10-28 - Complete Phase 3 legal-candidate scoring

Plan item: Phase 3 - repair and scoring  
Status: Complete

Files changed:

- `engine/layouts.py`
- `engine/resize.py`
- `tests/test_quality.py`
- `tests/test_resize.py`
- `README.md`
- backend planning, decision, implementation, and handoff documents

What we implemented:

- Added a transparent score from 0 to 1 for each legal candidate.
- Measured accidental overlap, text readability, hierarchy, canvas use,
  alignment, spacing, and group cohesion.
- Compared overlap with the source and ignored overlap within one group.
- Changed `resize()` to hard-reject invalid candidates and return the
  highest-scoring remaining candidate.
- Kept the deterministic safe fallback when generation or scoring fails.
- Added seven focused scoring tests and updated selection tests to check the
  best score instead of a fixed canvas-shape rule.

How it works in simple terms: The engine now makes several safe arrangements
and gives each one a report-card score. An arrangement that breaks a hard rule
is removed first. The legal arrangement with the best score wins.

What is different from the plan:

- Scoring lives beside the built-in layouts instead of in `engine/ranking.py`.
  That file belongs to Reem, so Ruthvik's fallback stays independent.
- Phase 3 changes how the winner is chosen; it does not add another layout.
- Stable candidate order resolves an exact score tie, keeping output
  deterministic without extra tie-breaking code.

Tests run and results:

- `.venv/bin/python -m unittest discover -s tests -v`: 40 tests passed.
- `.venv/bin/python -m compileall -q engine tests`: passed.
- The official samples selected preserve-and-repair for Level 1,
  horizontal-split for Level 2, and compact-banner for Level 3.

Rendered output checked: Yes. All three samples rendered at their target
canvas size and remained valid. The visible sample layouts match Phase 2
because those layouts also receive the best Phase 3 scores.

Known limits:

- Text readability is estimated from box size and character count; it is not a
  full font-shaping or rendered-pixel measurement.
- Score weights are initial engineering values, not trained or calibrated on
  a labeled design-quality dataset.
- The optional local decision model is not integrated and is not required for
  the fallback engine to work.

Next step: Phase 4 remains optional and blocked on the ranking contract and
official model limits. Phase 5 hardening can proceed independently.

## 2026-10-28 - Begin Phase 5 hardening

Plan item: Phase 5 - hardening and release  
Status: In progress

Files changed:

- `tests/test_hardening.py`
- `.dockerignore`
- `Dockerfile`
- `README.md`
- backend planning, decision, implementation, and handoff documents

What we implemented:

- Added a synthetic design with long text, positive and negative rotations, a
  three-element group, a proportional image, and a cover background.
- Tested tall, wide, square, and extreme-banner targets.
- Checked repeat determinism, source non-mutation, protected metadata, image
  ratio, and hard validation.
- Added a small Docker ignore file so local environments, PDFs, outputs, and
  caches do not enter the build context.
- Made the target architecture a build command choice instead of hardcoding it
  in `FROM`, removing the Docker build warning.
- Updated the documented runtime command with explicit architecture,
  read-only input mounting, and network isolation.

Tests run and results:

- `.venv/bin/python -m unittest discover -s tests -q`: 42 tests passed.
- `.venv/bin/python -m compileall -q engine tests`: passed.
- `git diff --check`: passed.
- `docker build --platform linux/amd64`: passed under Python 3.11.
- Strict Docker run with `--network none`, `--read-only`, read-only inputs, and
  a temporary writable output: all three samples completed successfully.
- All container JSON outputs passed hard validation.
- PNG dimensions matched 1080x1350, 1600x400, and 728x90 exactly.

What is different from the plan: We used one compact synthetic fixture across
four targets instead of adding many fixture files. This covers the planned
structural variations with less test data to maintain.

Known limits:

- The synthetic tests check structure and geometry, not final rendered text
  wrapping or human visual preference.
- The renderer commit is pinned, but its transitive Python dependencies and
  the base-image digest are not fully locked.
- A true clean-clone rehearsal cannot happen until the current work is
  committed or copied into a clean repository state.

Next step: Add rendered visual assertions or review fixtures for crowded text,
then run the final clean-clone rehearsal.
