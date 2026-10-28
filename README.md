# CHAMELEON — starter repo

This repository contains the Chameleon resizing engine plus its input loading,
output writing, rendering, validation, tests, and Docker packaging.

```
input:  a task JSON (source design + target canvas)
              |
              v
        engine/resize.py   <-- chooses a legal layout candidate
              |
              v
output: <task>_output.json  (schema-valid resized design)
        <task>_output.png   (rendered preview)
```

Both the JSON and the PNG are what get evaluated — see `RULES.md`.

## Repo layout

```
engine/
  resize.py        <- official entry point and candidate selection
  layouts.py       <- deterministic layout strategies
  geometry.py      <- bounds, scaling, overlap, groups and clamping
  constraints.py   <- hard output validation
  main.py           <- orchestrator (input -> resize() -> output). Don't need to edit this.
tests/               <- geometry, validation, resize and renderer tests
renderer/           <- the real renderer (transformer-convertor + cr-renderer), already vendored
brand_kit/
  assets/           <- image files referenced by asset_id in the sample designs
  fonts/            <- font files matching the schema's font_family values
input/               <- drop task JSON files here for local testing (3 samples included)
output/              <- results land here
chameleon_design_schema_v0.9.json   <- full field-by-field spec for the design format
Dockerfile
RULES.md
```

## Quick start (no Docker needed for iterating on `resize()`)

```bash
pip install -r requirements.txt
python -m engine.main
```

This processes every `*.json` file in `input/` (the 3 sample designs are
already there — one per difficulty level) and writes an `_output.json` and
`_output.png` for each into `output/`.

The current engine generates several deterministic layouts, rejects any that
break hard rules, and scores the remaining candidates. The score compares
accidental overlap, text readability, hierarchy, canvas use, alignment,
spacing, and group cohesion. The highest-scoring legal layout is returned, with
a deterministic proportional fallback if candidate generation fails.

## What the self-check does (and doesn't do)

`main.py` runs a quick structural check after every task — same element
`id`s as the source, required fields present, nothing off-canvas. **This
is not the official scorer.** It exists to catch obvious mistakes before
you waste a submission on them. See `RULES.md` for what's actually
checked and graded.

A self-check warning does not fail the run — your JSON and PNG are still
written either way. Read the warning; decide whether it's a real problem
or, like the Level 2 sample's intentionally corner-bleeding decorative
circle, an expected one.

## The renderer

`main.py` calls `renderer/converter/convert.py`'s `render_design_to_png()`
(a vendored copy of `transformer-convertor`, wrapping `cr-renderer`) to
produce each task's PNG — already wired in, no setup needed. It reads
fonts/assets from `brand_kit/` and writes a real rendered preview, not a
placeholder. If you ever see plain labeled boxes instead of real text and
images in `output/*.png`, that means the import in `main.py` failed (e.g.
`cr-renderer` didn't install — check `requirements.txt` installed cleanly)
and it silently fell back to the box-and-label placeholder; don't judge
your layout quality by that fallback.

## Docker (how you'll actually be run)

```bash
docker build --platform linux/amd64 -t my-chameleon-engine .
docker run --rm --platform linux/amd64 --network none \
  --mount type=bind,src="$(pwd)/input",dst=/app/input,readonly \
  --mount type=bind,src="$(pwd)/output",dst=/app/output \
  my-chameleon-engine
```

`--network none` matches how stage-one scoring runs: everything your
engine needs must be installed at **build** time (add it to
`requirements.txt`), not fetched at run time. If you're using a locally
hosted model, bake its weights into the image during the build step.

## See also

- `chameleon_design_schema_v0.9.json` — full input/output field spec
- `RULES.md` — what's checked, what's graded, and what disqualifies a submission
- FAQ — for anything not covered above
