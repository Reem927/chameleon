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
  text_fit.py      <- font measurement and text fitting that matches the renderer
  main.py           <- orchestrator (input -> resize() -> output). Don't need to edit this.
tests/               <- geometry, validation, text fit, readability, resize and renderer tests
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

## How the engine works

`resize()` builds several complete layouts, rejects any that break a hard rule,
scores the rest, and returns the best one.

1. **Split the design into units.**
   A full-canvas `cover` image is the background and is stretched to the new canvas.
   Ungrouped shapes are decorations and keep their relative position.
   Every `group_id` becomes one rigid unit, so a button and its label move and scale together.
2. **Build candidates.**
   `preserve_and_repair` scales the whole foreground uniformly into a safe box.
   The flow layouts place units in reading order along one row, one column, or two rows.
   Each flow layout is built three times with graphics at 100%, 60% and 30% of the text scale, so cramped banners can favour text.
3. **Reflow text instead of squashing it.**
   A lone text element may change its box shape.
   The engine measures the brand fonts with Pillow exactly the way the renderer wraps them and picks the largest font size that fits.
   All text shares one scale so headlines stay larger than body copy.
   When space allows, text is kept at 7px or more.
4. **Reject illegal candidates.**
   IDs, protected fields, image proportions and canvas bounds are checked in `engine/constraints.py`.
5. **Score and pick.**
   The score combines accidental overlap, text readability (weighted by source prominence, plus the worst text), hierarchy, canvas use, alignment, spacing and group cohesion.

If anything unexpected goes wrong, `resize()` returns a proportional fallback, and for malformed input an unchanged copy, so it never raises.

Run the tests with:

```bash
python -m unittest discover -s tests
```

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

## Demo UI and API (local only, not scored)

A browser demo shows the engine at work: pick a sample or drop a design, drag
the target frame or pick a format, and watch the layout morph. It also shows
the official render, rule checks, and why the engine chose its layout. Neither
the UI nor the API is part of the Docker image, and `engine/` never imports
them.

Needs Python 3.10+ and Node 22.12+. Run each in its own terminal from the repo root:

```bash
# 1. API on http://127.0.0.1:8000 (uses the same requirements.txt)
pip install -r requirements.txt
python -m api.app

# 2. UI on http://localhost:5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The pill in the top right says "engine online"
once the UI reaches the API; start them in either order. Without the API the
UI still opens samples and shows results from `output/` after
`python -m engine.main`.

Frontend checks: `npm test` and `npm run build` in `frontend/`. Details are in
`docs/SHIVRAJ_HANDOFF.md` and the API in `docs/api-contract.md`.

## See also

- `chameleon_design_schema_v0.9.json` — full input/output field spec
- `RULES.md` — what's checked, what's graded, and what disqualifies a submission
- FAQ — for anything not covered above
