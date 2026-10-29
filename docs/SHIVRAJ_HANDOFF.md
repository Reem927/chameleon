# Shivraj Frontend Handoff

Last updated: October 28, 2026  
Branch: `feature/shivraj-frontend`  
Current frontend status: core demo UI complete and tested; waiting on Reem's API and typed client for live resizing

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
  - Split: source and result side by side, with a line linking the hovered element in both panes.
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
  A Decision panel shows the strategy, candidate scores and warnings. It stays hidden until a result carries a `DebugPayload`.
- **Feel:** the shell takes its accent colours from the loaded design.
  An SVG chameleon mascot follows the pointer and reacts to busy, success and error states.
  The UI also has toasts and JSON/PNG export, works at 390px width with no sideways scroll, and respects reduced motion.
- **Tests:** 41 frontend tests pass with `npm test`. Typecheck and production build pass with `npm run build`.
  All tests read the real `input/*.json` samples from disk, and no fixture data is authored.
- **Known limit:** without the API, changing the target cannot produce a new layout. The UI says "engine offline" and marks the old result as stale.

## How results reach the UI today

There is no live backend yet. Results come from files:

1. Run `python -m engine.main` from the repo root. It writes `output/<sample>_output.json` and `.png`.
2. Vite serves `input/`, `output/` and `brand_kit/` read-only. They are listed in `server.fs.allow` in `frontend/vite.config.ts`.
3. When a sample loads, the UI pairs it with its `output/` result if the IDs and canvas size match.

Re-run the engine and refresh the page to see new engine output.

## Frontend direction

Once Reem's client exists, the UI will:

1. detect `frontend/src/services/index.ts` automatically (see `features/preview/engine.ts`);
2. call `health()` and show "engine online";
3. send `{source, target_canvas}` about 380ms after the user stops dragging or typing, cancelling any older request;
4. morph into the returned design, update the checks, and attach `preview_url` for Render check;
5. fill the Decision panel from `debug`.

Planned next: a format wall (one design shown in every preset at once), a ⌘K command palette, a 7-axis radar chart per candidate, and `docs/ui-notes.md`.

## Contract with Reem

The frontend calls the API only through Reem's typed client. The expected
shape is mirrored in `frontend/src/types/contracts.ts`:

```ts
// frontend/src/services/index.ts (Reem)
export function resize(request: { source: Design; target_canvas: Canvas }, signal?: AbortSignal):
  Promise<{ design: Design; preview_url: string | null; debug: DebugPayload | null }>
export function health(signal?: AbortSignal): Promise<boolean>
```

- `POST /api/resize` and `GET /api/health` follow PLAN.md §3.
- The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. That port is a placeholder, so tell Shivraj the real one.
- `preview_url` must be a URL the browser can load, either through the `/api` proxy or with CORS.
- `debug` can be `null`. When present, the inspector reads:
  - `strategy`;
  - `warnings: string[]`;
  - `candidate_scores`, as either a list of `{name, legal?, total?, breakdown?}` or an object keyed by candidate name.
  `breakdown` should carry Ruthvik's seven measures: collision, text, hierarchy, canvas_use, alignment, balance_spacing and group_cohesion.
- `docs/api-contract.md` stays the source of truth. If it differs from `contracts.ts`, Shivraj updates the mirror, never the other way.

## Contract with Ruthvik

The frontend never imports from `engine/`. It only reads the engine's output
files or goes through Reem's API. Nothing in `frontend/` is needed by the
Docker image. The UI reads the official samples, brand kit and renderer output
but never writes them.

## Hard rules for every contributor and coding assistant

- Read `RULES.md`, the schema, `PLAN.md`, this handoff and [`RUTHVIK_HANDOFF.md`](RUTHVIK_HANDOFF.md) first.
- **No hardcoded or fake data, including in tests.** Data comes only from user files, the real `input/`, `output/` and `brand_kit/` files, or the real API.
  - The one exception is `frontend/src/mocks/dev-presets/`, a list of real platform sizes kept for testing. Delete that folder before merging to `main`.
  - The app keeps working without it: the preset chips disappear, but typing a size and dragging the frame still work.
- Do not edit `frontend/` files owned by Shivraj without approval. `frontend/src/services/**` belongs to Reem.
- Never make the scored engine depend on the frontend or the API.
- Never generate or edit image pixels.
- Do not commit `frontend/node_modules/`, `frontend/dist/` or generated `output/` files.
- Include exact tests and results in every handoff.

## Run it

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm test           # 41 tests
npm run build      # typecheck + production build
```

For engine results in the UI, set up Python once from the repo root, then run
the engine:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows path; use .venv/bin on macOS/Linux
.venv/Scripts/python -m engine.main
```

## Current requests for teammates

From Reem:

- `docs/api-contract.md` with the final request, response, `DebugPayload` and port;
- a running `api/app.py` that calls the real `engine.resize.resize` and the real renderer, and serves `preview_url` PNGs;
- `frontend/src/services/index.ts` exporting `resize()` and `health()` as above;
- all candidates in `DebugPayload`, each with legal flag, total and seven-part breakdown;
- one real `DebugPayload` saved from an API run, not hand-written, for inspector testing.

From Ruthvik:

- announce any change to which fields `resize()` may modify, because the locked-fields check mirrors that rule;
- keep `python -m engine.main` writing `output/<sample>_output.json` and `.png` with these names, because the UI pairs results by file name.

From everyone:

- announce pushed branches and contract changes before integration;
- if you are an assistant working for Reem or Ruthvik, propose frontend changes in the PR instead of editing Shivraj's files.

## Open questions

- Final API port and whether the API serves PNGs on the same origin.
- Whether the FAQ's required, unscored viewer "add-on" must be an Adobe Express add-on, or whether this local demo is enough for Stage 1.
- PR review: `frontend/.gitignore`, `frontend/src/__tests__/setup.ts` and `frontend/src/__tests__/realSamples.ts` are not on the PLAN.md §2 ownership list, but the frontend needs them.

## Where to look next

- Team plan and file ownership: [`PLAN.md`](../PLAN.md)
- Backend engine status: [`RUTHVIK_HANDOFF.md`](RUTHVIK_HANDOFF.md)
- Frontend types and API mirror: [`frontend/src/types/contracts.ts`](../frontend/src/types/contracts.ts)
- Client auto-detection: [`frontend/src/features/preview/engine.ts`](../frontend/src/features/preview/engine.ts)
- Shivraj's detailed task list is kept locally. Ask Shivraj if you need it.
