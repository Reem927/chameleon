# Demo API contract

Owner: Ruthvik (taken over from Reem, D-022)  
Last updated: October 30, 2026  
Status: Live in `api/app.py`; client in `frontend/src/services/index.ts`

This document is the source of truth for the demo API.
`frontend/src/types/contracts.ts` mirrors it; if they differ, the mirror is updated, not this file.

The API is for the local demo only.
It is not part of the scored Docker image, and the engine never imports it.

## Run it

```bash
.venv/bin/python -m api.app          # http://127.0.0.1:8000
cd frontend && npm run dev           # http://localhost:5173, proxies /api to port 8000
```

The server binds to `127.0.0.1` only and uses the Python standard library plus the root `requirements.txt`; `api/requirements.txt` adds nothing.

## `GET /api/health`

```json
{"status": "ok", "renderer": true}
```

`renderer` is `false` when the real renderer cannot be imported; resizing still works, previews do not.

## `POST /api/resize`

Request: the same envelope as the official task files.

```json
{"source": {"canvas": {"width": 1080, "height": 1080}, "elements": [...]},
 "target_canvas": {"width": 1080, "height": 1920}}
```

Response `200`:

```json
{"design": {"canvas": {...}, "elements": [...]},
 "preview_url": "/api/previews/<32 hex>.png",
 "debug": {"strategy": "vertical_stack", "candidate_scores": [...], "policies": [...], "warnings": []}}
```

- `design` is exactly what `engine.resize.resize()` returns for the same input.
- `preview_url` is a PNG from the official renderer, served through the same `/api` proxy, or `null` if rendering failed.
- `debug` may be `null` if diagnostics could not be built; `design` is still returned.

### `DebugPayload`

| Field | Type | Meaning |
|---|---|---|
| `strategy` | string | Name of the chosen candidate, e.g. `compact_banner@0.6+clean`. |
| `candidate_scores` | list | One row per candidate, in build order (see below). |
| `policies` | list | Hints from the decision policy: `{"strategy", "weight", "reason"}`. |
| `warnings` | list of strings | Ranking and renderer warnings, e.g. a missing asset. |

Each `candidate_scores` row:

| Field | Type | Present when |
|---|---|---|
| `name` | string | always |
| `legal` | bool | always |
| `problems` | list of strings | `legal` is false |
| `weight` | number | `legal` is true (policy weight; 0.0 today) |
| `total` | number | `legal` is true (weighted score plus weight) |
| `breakdown` | object | `legal` is true |

Candidate names: a family (`preserve_and_repair`, `vertical_stack`, `horizontal_split`, `compact_banner`, and for dense designs `two_columns`, `three_rows`), an optional graphic ratio suffix (`@0.6`, `@0.3`), and an optional `+clean` suffix for the cleanup-pass variant.

`breakdown` has eleven parts, each from 0 to 1:
`collision`, `text`, `hierarchy`, `canvas_use`, `alignment`, `balance_spacing`, `group_cohesion` (the original seven), and `reading_order`, `similarity`, `source_alignment`, `area_share` (from the layout papers, D-023).
Weights are in `QUALITY_WEIGHTS` in `engine/layouts.py`.

### Errors

`400` with `{"error": "<message>"}` when:

- the body is empty, larger than 2 MB, or not JSON;
- `source` or `target_canvas` is missing or not an object;
- a canvas side is not a number in `(0, 10000]`;
- `elements` is empty, has more than 500 items, has a duplicate `id`, an unknown `type`, or a non-finite `x`, `y`, `width` or `height`;
- an image `asset_id` is not a plain file name (no folders, no `..`, no URLs).

Unknown routes return `404`.

## `GET /api/previews/<id>.png`

Serves a rendered preview by its 32-character hex id.
Any other path under `/api/previews/` returns `404`.
Previews live in a private temporary folder for the life of the server.
