# Decision model notes

Owner: Ruthvik (taken over from Reem, D-022)  
Last updated: October 30, 2026

## What it is

The decision model is a small set of readable rules in `engine/decision_policy.py`.
It is not a trained model.
It reads only geometry and element types (`engine/decision_features.py`), never ids, file names, colours or what the text says.
It runs offline, needs no weights file, and gives the same answer every time.

Why rules: the challenge's approved-model list and size limit are still unknown, and a learned model would need training data we do not have.
RULES.md also requires any fine-tuned weights to be public.

## What it decides

`suggest_policies(source, target_canvas)` returns hints like:

```python
{"strategy": "two_columns", "weight": 0.0, "reason": "18 content units: try more lines (balanced flow)"}
```

- `strategy` names a layout family.
  Base families (`preserve_and_repair`, `vertical_stack`, `horizontal_split`, `compact_banner`) are always built.
  Extra families (`two_columns`, `three_rows`) are built only when a hint names them.
- `weight` is added to that family's score in `engine/ranking.py`.
- The policy can only add layouts and weights; it never removes a layout (D-024).
  If it fails, `resize()` runs without it.

## Current rules

| Rule | When | Evidence |
|---|---|---|
| Balanced flow (ORC Layout) | 8 or more content units | `huge_25` (18 units): 300x250 text 4px -> 7px, 1200x628 11.6px -> 16px. `dense_12` (11 units): cleaner two-column layouts at 1200x628 and 300x250. Designs with 2-5 units lost text size when offered these families, so they are not offered. |

No weight rules are shipped.
No fixture showed a case where a score bonus would pick a better layout than the score alone, so every weight is 0.0.
A weight rule may be added only with a fixture that shows the improvement.

## Features

`extract_features` returns: `aspect_change` (log of target ratio over source ratio), `aspect_closeness`, `width_scale`, `height_scale`, `content_units`, `text_units`, `groups`, `rotated`, `text_characters`.

## How it is tested

- `tests/test_decision_model.py`: features ignore ids and do not mutate input; dense designs get more lines and sparse designs get nothing; the policy changes the chosen layout in two distinct scenarios (PLAN.md Gate B); the policy never removes a layout; `resize()` survives a failing policy.
- `tests/test_ranking.py`: the best legal candidate wins; illegal candidates never win; weights can change the choice; diagnostics list every candidate with the full breakdown and never reach the design.
