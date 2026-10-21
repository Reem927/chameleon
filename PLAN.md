# Project Chameleon — Team Execution Plan

**Adobe University Hackathon 2026 | Stage 1 deadline: October 30, 2026**  
**Team:** Ruthvik (Backend), Shivraj (Frontend), Reem (Full Stack)  
**Plan start:** October 20, 2026 | **Code freeze:** October 29, 2026  
**Goal:** Build an advanced, offline-capable intelligent design-retargeting engine with a *small local AI decision model*, while developing a separate, useful demo interface in parallel.

> **Source-of-truth note (October 20):** This plan is grounded in the provided *Final Chameleon Challenge.pdf* and the publicly available Adobe starter repository at <https://github.com/jhaaj08/chameleon>. Paths were reconciled on October 20 against the team fork <https://github.com/shivraj-jadeja/chameleon> at commit `a44a060` (remote `upstream` = Adobe starter). The challenge PDF is **not in the repo**; obtain it from the organizers and keep a local copy outside git. The latest official `RULES.md`, schema, and engineering clarifications take priority over this plan.
>
> **Priority:** The scored Stage 1 deliverable is the **headless Python engine** producing valid JSON and high-quality rendered PNGs. The React frontend and local demo API are useful development/demo additions, but must never become required dependencies of the scored engine. Do not spend submission-critical time polishing UI.

---

## 1. Success criteria and hard constraints

### What we are building

Given `source = {canvas, elements}` and `target_canvas = {width, height}`, `engine.resize.resize(source, target_canvas)` must return the same design in the official schema, with its individual elements **reflowed**, rather than uniformly stretched. It should generalize to unknown designs and sizes.

**Advanced approach:** generate several candidate layouts; use a lightweight **local decision model** to select suitable strategies and rank the candidates; repair geometry; return the best *valid* design. The model makes simple decisions about orientation, layout strategy, density, margins, and priority, **not** image/content generation.

### Non-negotiable Adobe restrictions

- [ ] Every input element ID appears **exactly once** in output; no added or removed elements.
- [ ] Preserve each element's type and supplied source asset (`asset_id`); do **not** generate, redraw, replace, or synthesize image pixels, including backgrounds. Image regeneration is **disqualifying**.
- [ ] Keep image proportions (non-background images within the rule's approximate 5% tolerance); use cropping only where permitted, including existing `fit: "cover"` behavior.
- [ ] Preserve text `content`, `font_family`, and brand styling; adjust `font_size`, text-box dimensions, and placement where needed. Do not use copy rewriting in Stage 1.
- [ ] Keep output within the target canvas, maintain correct schema/fields, retain meaningful grouping (`group_id`), z-order, and intentional layering. Investigate expected sample-specific decorative bleed warnings instead of silently deleting elements.
- [ ] Test both **output JSON** and the PNG rendered by Adobe's real renderer. The starter's `self_check()` is only a sanity check, **not** the judge.
- [ ] Stage 1 works completely **offline** in `linux/amd64` Docker using `--network none`; no requests to ChatGPT/OpenAI/Claude or other cloud LLM APIs at runtime; no model downloads at runtime.
- [ ] No hardcoding to the three examples, element IDs, specific brand names, or hidden cases. General geometric/semantic features and a documented fixed real-world canvas catalogue are acceptable.
- [ ] Check Adobe's permitted model list, size limits, evaluation resources, and any newer clarifications before shipping a learned model. Do not assume an arbitrary pretrained LLM or model weights are approved.

### Acceptance targets

1. **Structural reliability:** 100% of the team's local tests produce schema-valid results, unchanged element IDs/count, preserved immutable content/assets, and legal geometry.
2. **Visible quality:** Clear improvements over the uniform-stretch baseline on Level 1 and Level 2; best achievable robust output on Level 3, with trade-offs documented rather than concealed.
3. **Generalization:** Pass a suite of unseen, varied designs / target shapes, not only the three bundled samples.
4. **Reproducibility:** Clean install, `python -m engine.main`, and offline Docker build/run produce JSON and *actual* rendered PNGs.
5. **Submission:** A clear README and GitHub repo, with submission by October 30. Verify any official form instructions directly.

---

## 2. Roles: exclusive write ownership

**Rule:** A developer may **read** any source file, but may **write** only files they own below, unless an explicitly reviewed handoff is agreed in chat/issue/PR. In particular, never have two people or coding agents editing `engine/resize.py` or `frontend/src/App.tsx` simultaneously.

### Ruthvik — Backend Lead: core engine, geometry, candidate generation

**Actual features**

- Implement the official `resize(source, target_canvas) -> dict` entry point.
- Build safe geometry helpers: scaling, bounding boxes, anchors, aspect ratios, rotation-aware checking, canvas clamping, group transforms, margins, and overlap detection.
- Generate multiple **candidate layouts** based on a strategy/policy object: preserve-relations, vertical stack, horizontal split, compact banner, and grid/hero options where suitable.
- Implement safe layout repair / constraints: readability, spacing, respecting `group_id`, purposeful overlaps, no cropping of required text, safe handling of decorative shapes.
- Call Reem's decision policy and candidate ranking through frozen interfaces; always provide a fallback if her module is absent or a proposal fails.
- Run the official renderer locally and ensure the complete engine works in offline Docker; maintain the final engine README/build configuration.
- Write geometry, reflow, and invariants tests (not just test scripts).

**Exclusive write files**

- `engine/resize.py` — official entry point and orchestrator
- `engine/geometry.py` — transformations, bounds, overlap math
- `engine/layouts.py` — candidate generation strategies
- `engine/constraints.py` — legal/visual repair rules
- `engine/contracts.py` — **frozen** internal policy/candidate contract, jointly agreed on Day 1
- `tests/test_geometry.py`, `tests/test_resize.py`, `tests/test_constraints.py`
- `Dockerfile`, `requirements.txt` — only Ruthvik commits changes; others propose changes in PR comments/issues
- Root `README.md` — Ruthvik is final editor; Shivraj and Reem supply sections through comments or separate notes

**May read, never directly edit:** `engine/decision_*.py`, `engine/ranking.py`, `api/`, `frontend/`, Adobe `renderer/` and brand kit.

### Shivraj — Frontend Lead: interactive preview and visual workflow

**Actual features**

- Create the **local demo application** (React + TypeScript + Vite, unless a lighter framework is preferred), not an Adobe Express production add-on at Stage 1.
- Build a clear workflow: load a bundled sample JSON or paste/upload a JSON task; choose target preset or enter width/height; request resize; display output status.
- Implement canvas viewer with original vs resized preview, responsive side-by-side and stacked views, pan/zoom/fit-to-screen, and image information (dimensions/aspect ratios).
- Build preset controls (square, portrait, story, wide banner, ultra-wide) from a UI-only list. Do not force the engine to these presets.
- Show output JSON download/copy and rendered PNG download; display loading, invalid input, offline API unavailable, and request error states.
- Connect to Reem's API **through one typed client interface**, and use fixture/mock responses before the API exists.
- Write frontend component, type, interaction, responsive, and mock API tests; test at desktop/mobile screen widths.
- Keep the UI isolated from scored Docker; no changes to official `engine/main.py` or render pipeline.

**Exclusive write files**

- `frontend/package.json`, `frontend/package-lock.json` (or one selected package manager's lockfile), `frontend/vite.config.ts`, `frontend/tsconfig*.json`, `frontend/index.html`
- `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles/**`
- `frontend/src/components/**`, `frontend/src/features/preview/**`, `frontend/src/features/canvas-controls/**`
- `frontend/src/features/inspector/**`: decision-inspector UI (strategy, candidate scores, warnings, debug overlays), built against Reem's `DebugPayload` fixtures
- `frontend/src/types/contracts.ts` — frontend data/API contract **frozen on Day 1** with Reem; mirrors Reem's `DebugPayload` from `docs/api-contract.md` exactly
- `frontend/src/mocks/**`, `frontend/src/__tests__/preview*.test.tsx`, `frontend/src/__tests__/canvas*.test.tsx`, `frontend/src/__tests__/inspector*.test.tsx`
- `docs/ui-notes.md` — installation, screens, controls and demo instructions
- `PLAN.md` — plan owner; schedule revisions agreed with team. Only `PLAN.md` exists; never add a `plan.md` (same path on macOS/Windows case-insensitive filesystems). Rename of references from `plan.md` approved by Shivraj: [ ]

**May read, never directly edit:** `engine/**`, `api/**`, `frontend/src/services/**`, Adobe renderer and schema.

### Reem — Full-Stack Lead: AI decision agent, scoring, local API, debug payload

**Actual backend/AI features**

- Build a **lightweight, locally executed decision model** that reads only features derived from the provided design and target (e.g., target aspect ratio, element density, text/image area proportions, group count, source hierarchy hints). It decides which layout strategies to try, key layout preferences, and candidate ranking weights.
- Implement `suggest_policies(...)` and `rank_candidates(...)` using a small learned model or feature-based decision tree/ranker. Start with a transparent baseline; if using learned parameters, train **offline on generic/synthetic layouts**, store reproducible weights and document their origin. No external inference API.
- Implement a quality objective: structural validity as a hard gate, then overlap/collision penalties, text-space sufficiency, image distortion, alignment, visual hierarchy, spacing, and group cohesion. Preserve intentional layered overlaps.
- Implement a small **decision/repair loop**: observe -> propose layout strategies -> evaluate candidates -> choose best valid candidate; keep iterations bounded and deterministic.
- Build a **development-only local API** (`POST /api/resize`, `GET /api/health`, optionally debug endpoint) that calls the official engine and real renderer. No API dependency from the scored engine back to this server.
- Own the typed **debug payload** (`DebugPayload`: selected strategy, candidate scores and score breakdown, warnings, overlay geometry) defined in `docs/api-contract.md`, plus saved fixture payloads. Shivraj mirrors it in `frontend/src/types/contracts.ts` and builds the inspector UI. Debug data is never added to scored design JSON.
- Test model determinism, quality scorer, API input validation, missing assets, extreme sizes, and `DebugPayload` fixtures against the contract.

**Exclusive write files**

- `engine/decision_features.py` — input feature extraction
- `engine/decision_policy.py` — local AI strategy model
- `engine/ranking.py` — candidate-quality scorer/ranker
- `engine/decision_weights.json` — optional tiny learned weights/decision-tree parameters; bundle in Docker if used
- `tools/train_decision_model.py` — offline training/experiments (not a runtime requirement)
- `api/app.py`, `api/schemas.py`, `api/render_adapter.py`, `api/requirements.txt`, `api/**`
- `frontend/src/services/**` — typed API calls/adapters
- `tests/test_decision_model.py`, `tests/test_ranking.py`, `tests/test_api.py`
- `docs/model-notes.md`, `docs/api-contract.md` (source of truth for `DebugPayload`)

**May read, never directly edit:** `engine/resize.py`, `engine/layouts.py`, `engine/geometry.py`, `frontend/src/App.tsx`, `frontend/src/components/**`, `frontend/src/features/inspector/**`, `frontend/src/types/contracts.ts`, root Dockerfile/requirements, renderer/brand kit.

### Shared / Adobe-owned paths — change control

| Path | Who may write | Rule |
| --- | --- | --- |
| `engine/main.py` | Nobody by default | Official runner: don't rewrite for the UI or API. If absolutely necessary, team approval + tests first. |
| `renderer/**` | Nobody | Vendored scoring-equivalent renderer: inspect and use, do not customize. |
| `brand_kit/**` | Nobody | Preserve images and fonts exactly; do not add a replacement for intentionally missing Level 3 artwork. |
| `input/chameleon_sample_*.json` | Nobody | Keep official samples untouched. Put extra tests in `tests/fixtures/` or a separate temporary local folder. |
| `chameleon_design_schema_v0.9.json`, `RULES.md`, `FAQ.md` | Nobody | Official source of truth; read before implementation. |
| Root `.gitignore`, root docs/README, root dependencies | Named owner only | Propose in issue/PR; one integrator performs the edit. |
| `output/**`, Python caches, UI build outputs | Generated only | Do not commit outputs unless the team explicitly selects tiny, labeled comparison artifacts. |

> **Important:** All new runtime Python code must be importable from `engine/` because the current starter's `Dockerfile` copies that directory. Reem's API and the frontend are **not** part of the scored image. Never import `api` or `frontend` inside the scored engine.

---

## 3. Freeze interfaces first (Day 1)

By the end of October 21, Ruthvik and Reem approve the Python contract; Shivraj and Reem approve the demo API contract. No one changes these signatures casually after that.

### Engine contract — official

```python
# engine/resize.py (Ruthvik)
def resize(source: dict, target_canvas: dict) -> dict:
    """Return Adobe-schema-valid {canvas, elements}, nothing extra."""
```

### Internal AI -> geometry contract — proposed

```python
# engine/decision_policy.py (Reem)
def suggest_policies(source: dict, target_canvas: dict) -> list[dict]:
    """Return ranked policy hints, not final design JSON."""

# Example internal-only policy (NOT Adobe output):
# {"strategy": "compact_banner", "margin_ratio": 0.02,
#  "group_strength": 0.8, "text_priority": 0.9}

# engine/layouts.py (Ruthvik)
def generate_candidates(source: dict, target_canvas: dict,
                        policies: list[dict]) -> list[dict]:
    """Return complete Adobe-shaped candidate design dicts."""

# engine/ranking.py (Reem)
def rank_candidates(source: dict, target_canvas: dict,
                    candidates: list[dict]) -> tuple[dict, dict]:
    """Return chosen design and diagnostics metadata (metadata is INTERNAL)."""
```

**Integration sequence:** `source -> Reem policy -> Ruthvik candidate layouts / geometry repair -> Reem hard-gated ranking -> Ruthvik final validation/fallback -> official output`. Ruthvik retains the final responsibility for ensuring the returned object is exactly `{canvas, elements}`. Both developers must avoid circular imports; pass data through function arguments.

**Frozen invariants:** candidates are complete design dictionaries with the original element IDs; all input element properties are preserved unless changes are explicitly allowed. Reem's score diagnostics must **never** be returned as additional keys by `resize()` (top-level schema forbids them).

### Frontend -> demo API contract — proposed

- `POST /api/resize`: accepts `{ "source": <official design>, "target_canvas": {"width": ..., "height": ...} }` (same envelope as Adobe task input).
- Response (demo-only): `{ "design": <official output design>, "preview_url": "/api/previews/<id>", "debug": <DebugPayload> | null }`, where `DebugPayload` minimally holds `{"strategy": ..., "candidate_scores": ..., "warnings": [...]}`.
- `GET /api/health`: simple healthy/error response.
- API validation: reject malformed JSON, invalid dimensions, unsupported types, and oversized/unsafe inputs; avoid untrusted file-path injection and arbitrary remote asset URLs.
- Day 1: Reem writes `docs/api-contract.md` including `DebugPayload`; Shivraj mirrors the stable types in `frontend/src/types/contracts.ts`; both use the same saved fixture payloads. Changes to `DebugPayload` go to the doc first, then Shivraj updates the mirror.
- If a model score is unavailable, return `debug: null` or an empty diagnostics object while preserving `design` and `preview_url`.

**Mock-first promise:** Shivraj never has to wait for the backend to complete. His preview UI uses sample/fake responses until Reem's endpoint is live. Reem never has to wait for Ruthvik: her API initially uses a mock resize adapter, and her agent receives sample candidate dictionaries.

---

## 4. Advanced AI decision model — realistic scope

**Must-have AI capabilities (Stage 1):**

1. **Observe:** Extract general features from source/target without relying on semantic labels the input doesn't provide. Include aspect-ratio change, number/types of elements, occupied area, group counts, and a rough layout-density score.
2. **Decide:** Choose and rank layout strategies (`preserve`, `vertical_stack`, `horizontal_split`, `compact_banner`, `grid/hero`) plus modest policy parameters (margins, group cohesion, text emphasis).
3. **Act:** Ask Ruthvik's geometry module for valid candidates; **do not** directly rewrite text or pixels.
4. **Evaluate:** Rank candidates using structural hard checks first, then learned/weighted visual-quality metrics.
5. **Recover:** If a candidate violates hard rules, reject/repair it; if all proposals fail, return Ruthvik's deterministic safe fallback.
6. **Explain (debug only):** Expose selected strategy, score breakdown, and warnings to the local preview UI; never append them to official output JSON.

**Model choice (decision by Oct 21):**

- **Recommended:** A tiny feature-based decision tree or weighted linear policy/ranker. Train/evaluate offline on **generic synthetic design arrangements**; serialize small weights/tree parameters as JSON and implement lightweight local inference. This is a genuine model-driven decision component with understandable behavior and minimal CPU/memory cost.
- **No large LLM necessary.** Do not choose a vision-language or generative model just to make the project look advanced. If considering an open model or a learned checkpoint, first confirm Adobe's currently approved model list, size/reproducibility rules and evaluation machine support. If unapproved or too complex, keep the local feature-based policy and deterministic geometric fallback.
- **Training time vs runtime:** `tools/train_decision_model.py` may use developer-only libraries. Scored runtime depends only on bundled weights and installed build-time libraries; nothing downloads on startup.
- **Anti-overfit:** Do not train exclusively on three official sample designs. Generate varied element counts, groups, text lengths, imagery sizes, and target ratios; hold out some generated cases for evaluation.
- **Honest limitations:** Input contains elements and geometry, not semantic roles like “this is the logo.” Any inferred priority is probabilistic and must fail safely.

### Model decision criteria / rough quality score

**Hard gates before ranking:** correct exact IDs/count, no new assets, unmodified content/fonts, valid dimensions/fields, image ratio preserved, permitted geometry. Invalid candidates receive rejection, not merely a low score.

**Soft objectives:** minimize unintended collisions, improve text box capacity, keep images readable/in proportion, preserve grouped relationships, encourage alignment and balanced whitespace, maintain relative hierarchy. Respect existing intentional overlaps (especially shape + label groups), rotations, and backgrounds; don't penalize all intersections blindly.

**Target advanced behavior:** For an extreme 728x90 banner, AI should select a compact strategy and Ruthvik's geometry should generate an adaptive composition. If every element cannot remain prominent, prioritize legality and legibility while preserving **all** elements; do not remove content to make the image appear cleaner.

### Where the intelligent layer matters

The policy and ranker run on **every** input. There is no level detection and no sample-specific logic; behavior must follow from features (aspect-ratio change, density, groups, text length, rotation). The bundled samples show where that pays off:

- **Level 1** (4 elements, 1080×1080 -> 1080×1350; same width, +25% height; no groups, no rotation): policy should mostly pick `preserve` or `vertical_stack` and decide how to spend the extra 270px. The real trap is the `fit: contain` logo (3.2:1): uniform stretch distorts it by 25%, past the ~5% rule. Background is `fit: cover` and may crop to fill.
- **Level 2** (11 elements, 1080×1080 -> 1600×400; 1:1 to 4:1): source content spans y 60 to 1040, so a vertical stack cannot fit 400px. Expect `horizontal_split` or `compact_banner`. The ranker must keep two shape+label groups (`group_id` badge, cta; label sits inside its shape) together, preserve product (1:1) and logo aspect, and treat the two low-opacity (0.12/0.15) z_index 1 ellipses as intentional layering, not collisions. One ellipse bleeds off-canvas in the source; decide explicitly whether to clamp it. The headline has a `style_runs` entry; pass it through untouched.
- **Level 3** (17 elements, 1080×1350 -> 728×90; ~8.1:1, height scale ~0.067): strategy selection and ranking decide quality. Three long text blocks (142, 188 and 120 characters) cannot all stay legible at 90px tall; the ranker trades legibility against completeness without dropping elements. Five groups (a variable-count badge row, cta, rotated ribbon at -12°), a rotated pair whose rotated bounds must stay on canvas, and one image whose asset is missing (no crash, no substitute pixels).

---

## 5. Day-by-day parallel schedule (all three have independent work)

> **Schedule convention:** Work blocks below can happen asynchronously. Each day: 10–15 minute stand-up, roughly 60–90 minutes protected collaboration/integration time when needed, and the rest independent coding. Avoid committing major integrations at the end of the night without a green baseline.

| Date / stage | Ruthvik — Backend | Shivraj — Frontend | Reem — Full Stack | Joint checkpoint / free integration capacity |
| --- | --- | --- | --- | --- |
| **Oct 20 (kickoff)** | Clone / baseline run; inspect `resize.py`, `main.py`, schema, Docker | Sketch app layout; list viewer states; create UI project branch | Review candidate/policy feasibility; sketch model/API schemas | **30–45m contract meeting.** Agree module names, owners, allowed transformations; confirm hackathon model rules. |
| **Oct 21 (foundation)** | Create `engine/contracts.py`; basic bounds and geometry helpers; regression tests | Create Vite UI shell, canvas controls, mocked before/after preview, TS API contracts | Commit `docs/api-contract.md`; create decision feature extractor + mock `POST /api/resize` | **Gate A:** starter renders 3 PNGs; no placeholder renderer; contract frozen; model rules confirmed. Reserve last 1h for interface corrections. |
| **Oct 22 (parallel build I)** | Code source/target transforms, group-preserving placements, initial candidate templates | Implement sample JSON selection, manual target size, preview viewer and aspect-ratio handling | Build policy chooser from extracted features, scorer skeleton, API validation | Async status + 30m shared test of mocks; do not depend on other branches. |
| **Oct 23 (parallel build II)** | Finish 3–4 template families; geometry repairs and collision logic | Finish side-by-side/stacked viewer, zoom/fit, loading/errors, component tests | Implement candidate scoring, bounded decision loop, local model parameter serialization/training prototype | **Internal review:** each developer demos their own module; each module has passing unit tests. |
| **Oct 24 (buffer + PR day)** | Finalize pure-Python engine fallback and invariants; open backend PR | Finish API client with mock responses, responsiveness, UI PR | Finish AI policy + scorer tests; open backend PR; API mocks runnable | **Integration buffer (1–2h):** review PRs, reconcile signatures; no one loses coding time waiting. |
| **Oct 25 (Integration 1)** | Import policy/ranker, compose candidate pipeline, keep safe fallback; run samples | Swap mock for API when available; keep toggle/fallback for UI | Wire policy to Ruthvik engine; wire API to engine and renderer; fix contract mismatch | **Gate B:** full engine generates structurally valid JSON/real PNG. Demo UI -> API -> engine on local machine. Reserve 2h collaborative debugging. |
| **Oct 26 (quality I)** | Improve relative placement, group movement, image proportions and text constraints | Improve preview behavior for awkward wide/tall images; JSON export; frontend regression tests | Tune model choice and scoring on unseen synthetic designs; publish `DebugPayload` fixtures from real ranker runs | Focused independent work; reserve 1h for high-priority geometry/model fixes. |
| **Oct 27 (quality II)** | Improve Level 2/3 geometry and intentional layering handling; rotation/out-of-bounds tests | Build decision-inspector UI against Reem's `DebugPayload` fixtures; accessible controls | Populate `DebugPayload` score breakdown from the ranker; compare candidates; expand API and scorer edge tests | **Gate C:** Level 1/2 visually improved; Level 3 valid. Reserve 1–2h for rendering triage and regression fixes. |
| **Oct 28 (Integration 2 + hardening)** | Fix remaining critical legal/render failures; eliminate circular imports; run offline Docker | Cross-browser UI checks, README UI instructions, stop cosmetic changes | Verify model bundled offline; end-to-end test of API/UI; produce score/visual regression report | **Gate D:** all samples + unseen tests pass hard rules; freeze contracts and features by end of day. Allocate 2h joint bug bash. |
| **Oct 29 (code freeze)** | Own final Dockerfile/requirements/README; run linux/amd64 offline smoke tests | Validate frontend demo, provide screenshots/instructions, review root docs | Validate AI determinism, model size/provenance and packaging; review engine output/visuals | **Gate E:** tested, tagged release candidate. Only blocker fixes after freeze; reserve a 2h emergency patch window. |
| **Oct 30 (submit)** | Final clean clone + Docker run; verify engine files and outputs | Verify links, UI demo optional, help submission documentation | Final check model legality, API independence, checklist, backup submission | **Submit early** using actual hackathon instructions; confirm GitHub permissions, roster, emails, form and receipt. No new features. |

### Protected capacity / availability for integration

- **Oct 21:** 1 hour to fix interface disagreements before three implementations diverge.
- **Oct 24 afternoon:** 1–2 hours deliberately unassigned for PR review / stub integration.
- **Oct 25:** 2-hour dedicated Integration 1 block with all three online.
- **Oct 27:** 1–2 hours dedicated quality/debug block.
- **Oct 28:** 2-hour Integration 2 + release hardening block.
- **Oct 29:** 2-hour emergency only buffer; no planned feature work.
- If blocked more than 30 minutes on another owner's work, log the issue and continue against a **mock/contract stub**, not by editing their code.

### Critical path / priorities

- **P0 (submission blockers):** schema-correct engine; genuine reflow; offline Docker; model-safe integration; correct assets; valid JSON + renderer PNG.
- **P1 (competitive differentiators):** multiple strategies, lightweight AI policy/ranking, improved Level 2/3, broad unseen tests.
- **P2 (nice-to-have):** impressive React UI, polished inspector, extra transitions, an expressive demo. Cut these first if P0/P1 slip.

---

## 6. Stage gates and merge order

### Gate A — Oct 21: foundation (must pass)

- [ ] All three run the same starter commit, Python 3.10+ (Docker image uses 3.11; match it locally) and `python -m engine.main` successfully with `cr_renderer` importable.
- [ ] Check output PNGs contain **actual fonts/assets**, not plain label boxes from the fallback renderer.
- [ ] `RULES.md` and v0.9 schema reviewed; any changes from newest repo recorded.
- [ ] Model rules confirmed and written into `docs/model-notes.md`: (a) RULES.md: fine-tuned/LoRA weights must be publicly accessible; (b) README: local model weights must be baked in at build time, nothing fetched under `--network none`; (c) the "offline/size-limit rule in the main brief" and any approved-model list come from the challenge PDF, which is not in the repo, so obtain the exact numbers; (d) eval hardware is "Apple M5 Pro, exact CPU/RAM/disk limits TBD". Decision recorded: tiny feature-based policy with JSON weights unless a checkpoint is explicitly cleared.
- [ ] Internal Python and frontend/API contracts documented and frozen.
- [ ] `main`/release branch protected; feature branches created.

### Gate B — Oct 25: complete connected prototype

- [ ] Ruthvik's `resize()` returns exact official shape `{canvas, elements}`.
- [ ] Reem's decision model changes which layout strategy/candidate is chosen on at least two **general** distinct layout scenarios (verified by controlled test), rather than always choosing a fixed layout.
- [ ] All hard invariants validated on all three official samples and unseen local fixtures; known exceptions explained.
- [ ] Shivraj's UI sends a valid task through Reem's API and displays a real generated preview, with graceful mock/failure behavior.
- [ ] Merge/tag a **working baseline** before attempting risky quality changes.

### Gate C — Oct 27: advanced behavior

- [ ] Visibly better sample Level 2 than original uniform-stretch baseline.
- [ ] Level 3 returns complete legal structure without missing elements; visual tradeoffs inspected.
- [ ] Intentional overlaps are distinguished from collisions in local scoring/tests.
- [ ] Model determinism, offline execution, and fallback are covered by tests.

### Gate D — Oct 28: integration locked

- [ ] Run full unit + integration tests and inspect all rendered PNGs.
- [ ] Run additional varied targets and unseen synthetic layouts, recording pass/fail counts and screenshots.
- [ ] Standalone `python -m engine.main` works **without starting any API/frontend service**.
- [ ] No new imports from `engine/` into `api/` dependencies; direction is API -> engine only.

### Gate E — Oct 29: release candidate

- [ ] Offline `linux/amd64` Docker builds and runs with `--network none`.
- [ ] No runtime remote API calls, weight downloads, or npm/node frontend dependencies in judged container.
- [ ] Clean clone / documented startup; root README says what the engine does and how to run it.
- [ ] At least one reviewer checks diff against official rule restrictions.
- [ ] Submission link, dates, roster and GitHub accessibility confirmed.

---

## 7. Git/GitHub collaboration rules

**Branches**

```text
main                                # working, shippable baseline
├── feature/ruthvik-core-engine     # Ruthvik-only owned files
├── feature/shivraj-frontend       # Shivraj-only owned files
└── feature/reem-ai-api             # Reem-only owned files
```

1. **No direct push to `main`**; PR + one teammate review + automated/local tests.
2. One person owns each file. Cross-cutting edits require an issue, explicit approval, and ideally the owner's PR.
3. Avoid shared edits to `README.md`, `requirements.txt`, Dockerfile, package lockfile, `engine/resize.py`, `frontend/src/App.tsx`, or contract files. Root changes belong to named owners.
4. **Small commits** (one feature/fix per commit), descriptive names, and PR descriptions listing files, behavior, tests run, and screenshots of rendered outputs where relevant.
5. Merge in controlled order: **(1) contracts/baseline -> (2) Reem policy/scorer -> (3) Ruthvik engine integration -> (4) Reem API -> (5) Shivraj UI integration / inspector**. Independent modules may merge earlier if backward compatible, but maintain a green baseline.
6. Rebase or merge updated `main` into a feature branch **after** a successful integration checkpoint; don't force-push another developer's branch.
7. Never commit API keys, tokens, `.env`, downloaded model caches, `node_modules`, `venv`, giant build artifacts, or user data.
8. If another owner is unavailable: implement a **mock adapter in your own path**, open an issue and wait for review. Do **not** “just fix” their module.
9. Log integration decisions in the PR/issue, not only in private chat; make decisions visible to everyone and to coding assistants.
10. At every gate, tag or note the latest known-good commit so reverting risky changes is easy.

**PR definition of done**

- [ ] Only owned/approved files changed (`git diff --name-only`).
- [ ] Local tests for the feature pass and baseline smoke test isn't broken.
- [ ] No official samples/assets/schema changed.
- [ ] New dependencies explained; correct requirements/lockfile owner approves.
- [ ] API/signature/document changes coordinated with affected teammate.
- [ ] For engine changes, record rendered output quality and ensure no schema violations.
- [ ] Reviewer can reproduce the result from the PR instructions.

---

## 8. Instructions for ChatGPT, Copilot, Cursor, Claude or any coding assistant

**Every developer should paste or link this instruction at the beginning of every AI-assisted coding session:**

> You are helping on Adobe Project Chameleon. Read `PLAN.md`, `RULES.md`, `FAQ.md`, `README.md`, and `chameleon_design_schema_v0.9.json` **before** proposing changes. First ask which developer you are assisting (Ruthvik, Shivraj, or Reem), then restrict all file modifications to that developer's exclusive paths specified in `PLAN.md`. Read other people's code if needed, but do not modify, reformat, rename, remove or overwrite it. Do not alter Adobe's `engine/main.py`, `renderer/`, `brand_kit/`, official samples or schema. If another file must change, explain the reason and request explicit owner approval before touching it. Respect the offline Docker/scoring contract. Provide concise changes, tests, and integration notes; never claim tests passed if you did not run them.

**AI assistant rules (mandatory):**

- **Confirm scope first:** developer name, task ID, exact files allowed, expected exported interfaces, and current branch. Run `git status` / inspect changed files before editing.
- **No silent scope creep:** don't rewrite other modules, introduce a new frontend/backend architecture, reformat the repository, or install major libraries unless requested and approved.
- **Respect the Adobe API:** official `resize(source, target_canvas)` returns only schema-conforming design data. No debug scores, HTTP wrapper, or GUI dependencies in that response.
- **Never use an external AI API as part of Stage 1 runtime.** Coding-time use of assistants is a separate workflow; still follow hackathon participation and model restrictions.
- **Never modify existing image pixels** using generative tools. This is a disqualifier, even for backgrounds and “small” elements.
- **No fabricated training/evaluation evidence:** if score or tests are not run, mark as not run. Distinguish local heuristics from the official Adobe AI evaluator.
- **Preserve original content and identity:** IDs, text, font families, assets, grouping and branding; do not invent missing assets or silently drop elements to make a design pass.
- **No hardcoded sample solutions:** no `if asset_id == ...`, no special logic for `level3` sample filename, no fixed element IDs or manually authored “right answers.” General reusable features only.
- **Guard against failures:** no mutation of input dictionaries; error handling for strange dimensions, empty-ish grouping, missing renderer asset, awkward rotations and extreme target ratios. Do not make tests falsely green by weakening assertions.
- **Keep independent modules independent:** Reem's policy/ranker doesn't import Ruthvik's orchestrator; Ruthvik calls Reem's pure functions; frontend talks only to dev API/fixtures.
- **Small and testable changes:** prefer feature-scoped diffs and unit tests. A model does not improve the submission unless it improves real rendered designs.
- **Return a handoff after each change:** files edited; functions/behavior changed; tests run and results; any unresolved constraint; exact interface impact; next PR owner.
- **Stop and ask** if instructions conflict with official Adobe rules, if a new weight/checkpoint needs approval, or if an edit would cross ownership.

---

## 9. Testing matrix and tools

### Bundled samples (must not edit)

| Official file | Elements | Target | What it probes |
| --- | ---: | --- | --- |
| `input/chameleon_sample_level1_warmup.json` | 4 | 1080×1080 -> 1080×1350 | Easy reflow without stretching |
| `input/chameleon_sample_level2_core.json` | 11 | 1080×1080 -> 1600×400 | Groups, overlap, and extreme horizontal reflow |
| `input/chameleon_sample_level3_advanced.json` | 17 | 1080×1350 -> 728×90 | Very high density and extreme compression |

**Additional local tests** (fixtures under `tests/fixtures/`, maintain by the test owner):

- Mixed text/image/shape layouts with 2, 5, 12, and 25+ elements.
- Square -> portrait, square -> wide, portrait -> ultra-wide, wide -> tall, same aspect ratio at changed scale.
- Multiple `group_id`s; button shape with overlaid text; purposeful background/text layering; high `z_index` decorations.
- Long words, small text containers, headline + subheading, rotated elements; different font weights and style runs.
- Cases with missing asset references (must not crash or fabricate replacement), unusually small but valid canvas, crowded narrow banner.
- Deterministic policy selection and fallback when no candidate passes.

**Quality reporting after each stage:** Record `schema valid`, `all IDs preserved`, `no unapproved immutable-field changes`, `on-canvas`, `image ratio valid`, `render successful`, `local visual score`, and human reviewer notes. Screenshot/review side-by-side against initial baseline. The local score is **not** Adobe's official score.

### Smoke commands (from repo root)

```bash
python -m pip install -r requirements.txt
python -m engine.main

# Reproducible Stage 1 environment:
docker build --platform linux/amd64 -t chameleon-engine .
docker run --rm --network none \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  chameleon-engine
```

On **Windows PowerShell**, use separately:

```powershell
docker build --platform linux/amd64 -t chameleon-engine .
docker run --rm --network none `
  -v "${PWD}/input:/app/input" `
  -v "${PWD}/output:/app/output" `
  chameleon-engine
```

**Do not count it as a passing render if you see only colored labeled boxes.** `engine/main.py` falls back to a box renderer only on `ImportError` of `renderer.converter.convert` (in practice: `cr_renderer` not installed); fix the dependency instead. Keep `renderer/` unchanged.

---

## 10. Fallbacks, scope control, risk plan

| Risk | Response / owner |
| --- | --- |
| Reem's model not ready for Oct 25 | Ruthvik keeps a deterministic candidate-generation fallback and a basic weighted scoring stub. Reem continues implementing AI independently; integrate once tested. |
| AI model violates Adobe model-list or size constraints | Do not ship unapproved model weights. Ask Adobe engineering for clarification; switch to compliant tiny feature-based local policy/explicit deterministic fallback. **Never** call cloud models at runtime. |
| Backend API delayed | Shivraj continues UI development with fixtures; Reem keeps API mock adapter until official `resize()` is stable. |
| Level 3 visually difficult | Preserve all data and legal geometry first. Optimize typography/layout; don't delete elements or invent pixels. Document tradeoffs honestly. |
| Model scores well but produces ugly PNGs | Inspect actual rendered previews; adjust policy/ranking to prioritize observed quality over synthetic score. |
| New dependency breaks offline Docker | Remove/replace the dependency or pin an installable build-time version; Ruthvik owns changes to runtime requirements and Dockerfile. |
| Merge conflict or cross-owner file modification | Stop merge; let file owner resolve intentionally, rerun tests, and capture resolution in PR. No automatic keep-all merge. |
| Time pressure | Cut nonessential UI effects, advanced training, and fancy dashboard before cutting correctness, offline behavior, or official output quality. |

### Feature cut line

**Must ship:** a valid geometry engine, at least several general layout strategies, the small local decision/ranking component or documented safe fallback, comprehensive tests, reliable offline Docker, README.

**Can be reduced:** training sophistication, number of UI panels, inspector visual polish, animations, nonessential API options, visual storytelling features. The UI/API can be omitted from Docker entirely.

### Open questions (resolve at Oct 21 standup)

- [ ] FAQ Q5/Q3 call for a required, unscored Express viewer add-on; PLAN.md says not to build one. Ask Adobe engineering which applies. Affects Shivraj's lane.
- [ ] `resize()` must never raise: `engine/main.py` has no per-task error handling. Ruthvik wraps the pipeline with a safe fallback.
- [ ] Level 2 bleed: RULES checks off-canvas, README calls the bleed expected. Decide clamp vs keep before Gate C.
- [ ] Pin `cr-renderer` in `requirements.txt` to a specific commit (Ruthvik).
- [ ] Obtain the challenge PDF for the model list and size limit; schema is v0.9 provisional, so `git fetch upstream` before Gate A.

---

## 11. Daily handoff template

Each developer posts this at the end of their work block (issue, PR, or team channel):

```text
Date:
Owner: Ruthvik / Shivraj / Reem
Branch and latest commit:
Completed today:
Files I edited:
Tests run (results):
Current demo/preview or output example:
Interface changes affecting others:
Blockers / requests for another owner:
What I will do next:
Ready for review/merge? Yes/No
```

### Submission checklist — October 30

- [ ] Team registration and all participant details verified (Oct 8 registration deadline has passed).
- [ ] Submission repo includes the scored engine, its dependencies/weights if permitted, Dockerfile, and useful README.
- [ ] Official sample assets, schema, runner, and renderer unmodified.
- [ ] Offline container actually runs on clean checkout and creates JSON + real PNG.
- [ ] No proprietary/secrets/large unapproved models committed.
- [ ] Clear `git status`; correct GitHub URL and access settings.
- [ ] Submit through the **actual** Adobe form by October 30; verify success/receipt.
- [ ] Finale availability (January 11–13, 2027) confirmed for prize-eligible finalists.

---

## 12. Source references / precedence

1. **Official challenge PDF:** *Final Chameleon Challenge.pdf*, especially sections 2, 3, 4, 7.1–7.3. Not in the repo; keep a local copy. Official requirements outrank this team's preferences.
2. **Starter repository:** <https://github.com/jhaaj08/chameleon> (`upstream`); team fork <https://github.com/shivraj-jadeja/chameleon> (`origin`), reconciled at `a44a060` on October 20, 2026.
3. **Official file contracts:** `RULES.md`, `FAQ.md`, `chameleon_design_schema_v0.9.json`, `engine/resize.py`, `engine/main.py`, `Dockerfile`, `README.md`.
4. **Engineering clarifications / approved models:** Any newer written direction from Adobe supersedes provisional model limits and outdated FAQ passages.

**Final team principle:** *Work in independent folders, integrate through frozen contracts, review rendered results, and always maintain a clean Stage 1 engine that runs offline.*
