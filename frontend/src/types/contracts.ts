// Frontend mirror of the Chameleon design schema (chameleon_design_schema_v0.9.json)
// and the demo API contract (PLAN.md §3). The API half is provisional until
// Reem's docs/api-contract.md lands; update it from that doc, never the other way.

export type ElementType = 'text' | 'image' | 'shape'

export interface Canvas {
  width: number
  height: number
}

export interface StyleRun {
  start: number
  end: number
  color?: string
  font_weight?: 'regular' | 'bold'
  font_style?: 'normal' | 'italic'
}

interface BaseElement {
  id: string
  type: ElementType
  x: number
  y: number
  width: number
  height: number
  rotation?: number
  opacity?: number
  z_index?: number
  group_id?: string | null
  // Unknown extra keys (e.g. `_adversarial_note`) are kept untouched.
  [key: string]: unknown
}

export interface TextElement extends BaseElement {
  type: 'text'
  content: string
  font_family: string
  font_size: number
  font_weight?: 'regular' | 'bold'
  font_style?: 'normal' | 'italic'
  color: string
  text_align?: 'left' | 'center' | 'right'
  line_height?: number
  letter_spacing?: number
  max_lines?: number | null
  style_runs?: StyleRun[]
}

export interface ImageElement extends BaseElement {
  type: 'image'
  asset_id: string
  fit?: 'contain' | 'cover' | 'fill'
}

export interface ShapeElement extends BaseElement {
  type: 'shape'
  shape_type: 'rectangle' | 'ellipse' | 'line'
  fill_color: string
  stroke_color?: string | null
  stroke_width?: number
  corner_radius?: number
}

export type DesignElement = TextElement | ImageElement | ShapeElement

export interface Design {
  canvas: Canvas
  elements: DesignElement[]
}

/** Task envelope used by the official samples in input/*.json. */
export interface DesignTask {
  task_id?: string
  difficulty?: string
  difficulty_label?: string
  notes?: string
  source: Design
  target_canvas: Canvas
}

/** Fields the engine is allowed to change (RULES.md, PLAN.md §1). */
export const MUTABLE_FIELDS = ['x', 'y', 'width', 'height', 'font_size'] as const

// ---------------------------------------------------------------------------
// Demo API (docs/api-contract.md, October 30, 2026)
// ---------------------------------------------------------------------------

export interface ResizeRequest {
  source: Design
  target_canvas: Canvas
}

/** One row per candidate, in build order. */
export interface CandidateScore {
  /** Family, optional `@0.6`/`@0.3` graphic ratio, optional `+clean`. */
  name: string
  legal: boolean
  /** Present when `legal` is false. */
  problems?: string[]
  /** Present when `legal` is true: policy weight added to the score. */
  weight?: number
  /** Present when `legal` is true: weighted score plus weight. */
  total?: number
  /** Present when `legal` is true: each part from 0 to 1. */
  breakdown?: Record<string, number>
}

export interface PolicyHint {
  strategy: string
  weight: number
  reason: string
}

export interface DebugPayload {
  strategy: string
  candidate_scores: CandidateScore[]
  policies: PolicyHint[]
  warnings: string[]
}

export interface ResizeResponse {
  design: Design
  preview_url: string | null
  debug: DebugPayload | null
}

/**
 * Shape the frontend expects from Reem's typed client in
 * `frontend/src/services/index.ts`. The UI picks it up automatically
 * when that file exists (see features/preview/engine.ts).
 */
export interface ResizeClient {
  resize(request: ResizeRequest, signal?: AbortSignal): Promise<ResizeResponse>
  health(signal?: AbortSignal): Promise<boolean>
}
