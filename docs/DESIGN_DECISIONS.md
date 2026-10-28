# Backend Design Decisions

Owner: Ruthvik
Maintained by: Codex during implementation  
Last updated: October 28, 2026

This file explains why we chose an approach. It is a decision log, not a task
list. Add a new numbered decision when an important technical choice is made.
Do not rewrite old decisions silently. If a choice changes, mark the old entry
as replaced and link to the new entry.

Codex will update this file while implementing whenever we choose between
meaningful technical options. Small code details that do not affect the design
do not need a decision entry.

## Decision template

```text
## D-XXX - Short title
Date:
Status: Proposed / Accepted / Replaced
Problem:
Decision:
Why:
Other options:
Trade-offs:
Files affected:
How we will test it:
```

## D-001 - Build a deterministic engine before adding a model

Date: October 28, 2026
Status: Accepted

Problem: The repository has only the stretch baseline. A model cannot repair a
missing geometry and validation system.

Decision: Build validation, geometry, candidates, repair, and scoring first.
Add Reem's local decision policy through an optional interface later.

Why: This gives us a legal engine early. It is easier to test and remains a
fallback if the model is late, unapproved, or unreliable.

Trade-off: The first version may sound less advanced, but it will be more
correct and useful.

How we will test it: The engine must produce valid deterministic output even
when no decision-model module is installed.

## D-002 - Hard rules run before visual scoring

Date: October 28, 2026
Status: Accepted

Problem: A layout can look good while changing IDs, assets, text, or image
proportions.

Decision: Reject any candidate that breaks a hard rule. Score visual quality
only after the candidate passes validation.

Why: A high visual score must never hide an invalid submission.

How we will test it: Create attractive but invalid candidates and confirm that
all of them are rejected.

## D-003 - Preserve groups during movement and repair

Date: October 28, 2026
Status: Accepted

Problem: A button background and its label can become separated if elements
are moved independently.

Decision: Elements with the same non-null `group_id` move as one unit by
default. Their relative positions are preserved unless a tested repair clearly
requires a change.

Why: `group_id` is the strongest design-intent signal supplied by the input.

Trade-off: Some groups may still need to shrink or change internal spacing on
extreme canvases.

## D-004 - Use research as scoring guidance, not as a model to copy

Date: October 28, 2026
Status: Accepted

Problem: LayoutGAN and seam carving contain useful ideas, but their original
algorithms do not match the challenge rules.

Decision: Borrow set-based relationships, alignment and overlap measurements,
importance scores, and damage minimization. Do not train LayoutGAN now and do
not perform pixel seam carving.

Why: LayoutGAN can create, relabel, or remove elements. Seam carving changes
image pixels. Chameleon must preserve the exact elements and original assets.

## D-005 - Keep the official output free of debug information

Date: October 28, 2026
Status: Accepted

Problem: Candidate scores and warnings are helpful during development but are
not part of the Adobe output schema.

Decision: `resize()` returns only `canvas` and `elements`. Debug information
stays in tests, logs, or the optional development API.

How we will test it: Validate the returned top-level keys against the schema.

## D-006 - Stage 1 does not depend on a frontend

Date: October 28, 2026
Status: Accepted

Problem: Older team notes disagreed about whether an Express viewer was needed
for Stage 1.

Decision: Follow the official final brief: Stage 1 submits the engine and a
short README. The Express add-on is finale work. A team demo UI may exist, but
the scored engine cannot depend on it.

Why: This keeps submission work focused on the part Adobe scores.

## D-007 - Repair decorative bleed in output

Date: October 28, 2026
Status: Accepted

Problem: The Level 2 input intentionally places decoration outside the source
canvas, while the official Stage 1 structural check says output elements must
stay on-canvas.

Decision: Treat all output bounds as strict. Clamp, scale, or reposition
decorative elements unless Adobe later gives a written exception.

Why: The final challenge brief is newer and more authoritative than the README
note suggesting that the warning may be expected.

How we will test it: Include rotated and partially bleeding shapes in bounds
tests and check their full visible bounds.

## D-008 - Lock every supplied field except geometry and text size

Date: October 28, 2026  
Status: Accepted

Problem: The schema contains many brand and identity fields. Listing only a few
protected fields could allow another field to change by mistake.

Decision: Candidate elements must keep the exact same field names as their
source elements. Only `x`, `y`, `width`, `height`, and a text element's
`font_size` may change.

Why: This simple allowlist protects content, assets, fonts, colors, groups,
rotation, opacity, stacking order, image fit, style runs, and shape settings.

Trade-off: A future strategy cannot change rotation unless we make a new
decision and update the validator deliberately.

How we will test it: Change and add protected fields, including nested style
runs, and confirm the candidate is rejected.

## D-009 - Reject zero-sized normal images

Date: October 28, 2026  
Status: Accepted

Problem: The provisional schema allows an element width or height of zero, but
a zero-sized image has no usable aspect ratio and cannot be meaningfully shown.

Decision: Normal image elements must have positive source and output dimensions
for aspect-ratio validation. Other element types still follow the schema, where
a zero dimension may be useful for a line.

Why: Rejecting an undefined image ratio is safer than dividing by zero or
silently hiding an image.

How we will test it: Set a normal image height to zero and confirm validation
returns a clear problem instead of crashing.

## D-010 - Use simple shape rules until candidate scoring exists

Date: October 28, 2026  
Status: Accepted for Phase 2

Problem: Phase 2 can generate several layouts, but Phase 3 scoring does not
exist yet.

Decision: Choose the first strategy using only general canvas information:

- a similar aspect ratio uses preserve-and-repair;
- a much wider target uses horizontal split;
- a much taller target uses vertical stack;
- a very short or extremely wide target uses compact banner.

Every chosen result must still pass hard validation. If it fails, try the other
strategies and finally the proportional safe fallback.

Why: These rules are deterministic, understandable, and do not use sample IDs,
filenames, or brand names. They let us see real reflow before building the
Phase 3 scorer.

Trade-off: The shape rule may not choose the best candidate for every design.
Phase 3 will compare candidate quality instead of trusting only the target
shape.

## D-011 - Detect backgrounds from geometry and image fit

Date: October 28, 2026  
Status: Accepted

Problem: The schema does not label an element as a background.

Decision: Treat an image as a background only when it uses `fit: "cover"`, has
no meaningful rotation, and covers the complete source canvas. Resize that box
to the complete target canvas.

Why: This uses supplied design properties and avoids hardcoding IDs such as
`bg`. A smaller cover image remains a normal content image.

How we will test it: The official backgrounds fill every target while all
normal images keep their source proportions.

## D-012 - Hard validation comes before quality scoring

Date: October 28, 2026  
Status: Accepted

Problem: A visually attractive candidate is unusable if it changes protected
content, loses an element, distorts an image, or leaves the canvas.

Decision: Generate every built-in candidate, reject candidates with any hard
validation problem, then return the highest-scoring legal candidate. Keep a
deterministic proportional fallback for malformed input or generation failure.

Why: Safety rules are pass-or-fail. A quality score must never compensate for
breaking one of them.

## D-013 - Use a small transparent fallback score

Date: October 28, 2026  
Status: Accepted

Problem: Target-shape rules alone cannot tell which legal candidate best keeps
the source design's relationships.

Decision: Score legal candidates from 0 to 1 using accidental overlap, text
readability, hierarchy, canvas use, alignment, spacing, and group cohesion.
Compare overlap with the source so intentional layering is not automatically
punished. Ignore overlap inside one group.

Why: These measurements are deterministic, cheap, explainable, and available
offline. They also give the engine a complete fallback if Reem's optional
ranking component is absent.

Trade-off: The score estimates visual quality from geometry. It does not yet
measure rendered pixels or understand semantic importance.

## D-014 - Test a stricter container than the evaluator requires

Date: October 28, 2026  
Status: Accepted

Problem: A container can pass locally while still relying on hidden file
writes or runtime network access.

Decision: Verify the release image as `linux/amd64` with networking disabled,
read-only inputs, a read-only container filesystem, and only `/tmp` plus the
mounted output directory writable. Keep local environments, PDFs, outputs,
and caches out of the Docker build context.

Why: Passing under stricter conditions gives us confidence that the engine is
self-contained and will not depend on the developer machine at runtime.
