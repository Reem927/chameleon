# Shivraj Frontend Handoff

Last updated: October 30, 2026  
Branch: `feature/shivraj-frontend`  
Current frontend status: connected to the live demo API; resizes, renders and explains decisions end to end

This is the short document Shivraj can share with teammates and their coding
assistants. Read this before changing or integrating frontend code.

This file will be refreshed after meaningful frontend progress or an interface
change that affects Reem or Ruthvik.

## What Shivraj owns

Shivraj is responsible for:

- the local demo application in `frontend/` (React + TypeScript + Vite);
- the live preview, compare views, target-size controls, and decision inspector UI;
- the frontend mirror of the API contract in `frontend/src/types/contracts.ts`;
- frontend tests and `docs/ui-notes.md`;
- keeping the UI out of the scored Docker engine.

See [`PLAN.md`](../PLAN.md) for the complete team file-ownership rules.

## Current state

- **Stack:** React 19, TypeScript 7, Vite 8, `motion` for animation, Zustand for state, and Vitest with Testing Library and jsdom.
  Fonts for the app shell are bundled, so the UI runs offline.
- **Input:** a user can pick a sample, drop files, or paste JSON.
  - Samples come from `input/` and are shown as live thumbnails.
  - A dropped JSON can be a task envelope (`{source, target_canvas}`), a bare design, or an output design. An output is recognised because it has the same element IDs as the loaded source.
  - A dropped PNG that matches the result size becomes the official render. Other images become assets, matched to `asset_id` by file name.
- **Live preview:** each element is an absolutely positioned DOM node.
  - It uses the real Solstice fonts from `brand_kit/fonts` through `@font-face` and the real assets from `brand_kit/assets`.
  - It supports `object-fit` from `fit`, `style_runs`, rotation, `z_index` and opacity.
  - A missing asset shows a striped placeholder.
  - The preview is labelled "approximate" because browser text wrapping is not cr-renderer.
- **Views:**
  - Morph: elements spring from their source position to their result position, matched by ID. Space toggles between source and result.
  - Split: source and result side by side, each fitted to its own pane, with a line linking the hovered element in both panes.
  - Render check: wipe slider and onion-skin overlay comparing the live preview with the official PNG.
- **Target size:** typed width and height, a swap button, arrow-key steps (×10 with Shift), preset chips, and a drag-to-resize frame with 8 handles.
  The frame keeps the ratio with Shift, skips snapping with Alt, and snaps to presets.
  Pan and zoom work with Ctrl+wheel, dragging, and the F, + and - keys.
- **Rule checks:** computed from the real source and output.
  - IDs preserved and target canvas size.
  - Locked fields: anything other than `x`, `y`, `width`, `height` and text `font_size` must not change.
  - On canvas, using rotation-aware bounds with a 0.5px tolerance.
  - Image ratio of non-`cover` images against the 5% limit.
  - Smallest text size, with a warning below 8px.
  - Missing assets.
  These checks are a local aid, not Adobe's scorer.
- **Inspector:** a layers list showing each element's change (for example `40→11.3px`).
- **Decision panel:** built from the API's `DebugPayload`.
  - It shows the picked layout and how many candidates were legal.
  - An 11-axis radar shows the picked layout's score parts. Hovering another candidate overlays its shape.
  - Every candidate is listed, ranked by total. Illegal candidates show their first problem.
  - Policy hints and warnings are listed, for example the missing Level 3 asset.
  - The panel stays hidden when `debug` is `null`.
- **Feel:** the shell takes its accent colours from the loaded design.
  An SVG chameleon mascot follows the pointer and reacts to busy, success and error states.
  The UI also has toasts and JSON/PNG export, works at 390px width with no sideways scroll, and respects reduced motion.
- **Tests:** 41 frontend tests pass with `npm test` with the local dev-presets folder present. Without it, 39 pass and the 2 preset tests skip.
  Typecheck and production build pass with `npm run build`.
  All tests read the real `input/*.json` samples from disk, and no fixture data is authored.
- **Checked end to end on October 30 against the live API:**
  - Level 1, 2 and 3 samples, preset clicks and frame drags.
  - Render check against the API's PNG.
  - The Decision panel with 17 candidates for Level 3.
  - No console errors, at 1440px and 390px widths.
- **Known limit:** without the API, changing the target cannot produce a new layout. The UI says "engine offline", marks the old result as stale, and retries every 8 seconds.

## How results reach the UI

**With the API running (normal demo):**

1. The UI finds `frontend/src/services/index.ts` automatically (see `features/preview/engine.ts`), calls `health()`, and shows "engine online".
2. About 380ms after the user stops dragging or typing, it sends `{source, target_canvas}` and cancels any older request.
3. It morphs into the returned design, updates the checks, and loads `preview_url` for Render check.
4. It fills the Decision panel from `debug`.
5. A live result always replaces an older one read from `output/`.

**Without the API (fallback):**

1. Run `python -m engine.main` from the repo root. It writes `output/<sample>_output.json` and `.png`.
2. Vite serves `input/`, `output/` and `brand_kit/` read-only. They are listed in `server.fs.allow` in `frontend/vite.config.ts`.
3. When a sample loads, the UI pairs it with its `output/` result if the IDs and canvas size match.

## Frontend direction

Planned next, if time allows:

- a format wall that shows one design in every preset at once;
- a ⌘K command palette;
- `docs/ui-notes.md`.

## Contract with the API

The API and its client were built by Ruthvik, taking over from Reem (D-022 in
`docs/api-contract.md`). The frontend calls the API only through that typed
client, whose shape is mirrored in `frontend/src/types/contracts.ts`:

```ts
// frontend/src/services/index.ts
export function resize(request: { source: Design; target_canvas: Canvas }, signal?: AbortSignal):
  Promise<{ design: Design; preview_url: string | null; debug: DebugPayload | null }>
export function health(signal?: AbortSignal): Promise<boolean>
```

- The API runs on `http://127.0.0.1:8000`. The Vite dev server proxies `/api` there, so `preview_url` loads on the same origin.
- `debug` can be `null`. When present it has:
  - `strategy`: the name of the picked candidate;
  - `candidate_scores`: a list of `{name, legal, problems?, weight?, total?, breakdown?}`;
  - `policies`: a list of `{strategy, weight, reason}`;
  - `warnings: string[]`.
- `breakdown` has eleven parts from 0 to 1. The radar draws whatever keys are present, so new parts appear without a frontend change.
- Candidate names are parsed as family, optional `@ratio`, optional `+clean`, and shown as, for example, "Compact Banner · 60% graphics · cleaned".
- `docs/api-contract.md` stays the source of truth. If it differs from `contracts.ts`, Shivraj updates the mirror, never the other way.

## Contract with Ruthvik

The frontend never imports from `engine/`. It only reads the engine's output
files or goes through the API. Nothing in `frontend/` is needed by the Docker
image. The UI reads the official samples, brand kit and renderer output but
never writes them.

## Hard rules for every contributor and coding assistant

- Read `RULES.md`, the schema, `PLAN.md`, this handoff and [`RUTHVIK_HANDOFF.md`](RUTHVIK_HANDOFF.md) first.
- **No hardcoded or fake data, including in tests.** Data comes only from user files, the real `input/`, `output/` and `brand_kit/` files, or the real API.
  - Preset sizes are optional and load only from `frontend/src/mocks/dev-presets/`. That folder is not on `main`.
    It is gitignored, so a local copy can stay for testing. Without it the preset chips and snapping are hidden, but typing a size and dragging the frame still work.
- Do not edit `frontend/` files owned by Shivraj without approval. `frontend/src/services/**` belongs to the API owner.
- Never make the scored engine depend on the frontend or the API.
- Never generate or edit image pixels.
- Do not commit `frontend/node_modules/`, `frontend/dist/` or generated `output/` files.
- Include exact tests and results in every handoff.

## Run it

Set up Python once from the repo root, then start the API in its own terminal.
Start it before or after the UI; the UI connects within a few seconds either way.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows path; use .venv/bin on macOS/Linux
.venv/Scripts/python -m api.app                           # http://127.0.0.1:8000
.venv/Scripts/python -m engine.main                       # optional: offline results in output/
```

Then the UI:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm test           # 41 pass with local dev-presets; 39 pass + 2 skip without
npm run build      # typecheck + production build
```

## Current requests for teammates

From the API owner:

- update `docs/api-contract.md` first for any `DebugPayload` change, so the mirror can follow.

From Ruthvik:

- announce any change to which fields `resize()` may modify, because the locked-fields check mirrors that rule;
- keep `python -m engine.main` writing `output/<sample>_output.json` and `.png` with these names, because the offline fallback pairs results by file name.

From everyone:

- announce pushed branches and contract changes before integration;
- if you are an assistant working for Reem or Ruthvik, propose frontend changes in the PR instead of editing Shivraj's files.

## Open questions

- Whether the FAQ's required, unscored viewer "add-on" must be an Adobe Express add-on, or whether this local demo is enough for Stage 1.
- PR review: `frontend/.gitignore`, `frontend/src/__tests__/setup.ts` and `frontend/src/__tests__/realSamples.ts` are not on the PLAN.md §2 ownership list, but the frontend needs them.

## Where to look next

- Team plan and file ownership: [`PLAN.md`](../PLAN.md)
- Backend engine status: [`RUTHVIK_HANDOFF.md`](RUTHVIK_HANDOFF.md)
- API contract: [`api-contract.md`](api-contract.md)
- Frontend types and API mirror: [`frontend/src/types/contracts.ts`](../frontend/src/types/contracts.ts)
- Client auto-detection: [`frontend/src/features/preview/engine.ts`](../frontend/src/features/preview/engine.ts)
- Shivraj's detailed task list is kept locally. Ask Shivraj if you need it.
