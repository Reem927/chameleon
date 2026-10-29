import type { Canvas, Design, DesignElement, DesignTask } from '../../types/contracts'

export class DesignParseError extends Error {}

const TYPES = new Set(['text', 'image', 'shape'])

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function readCanvas(value: unknown, where: string): Canvas {
  if (!isObject(value)) throw new DesignParseError(`${where} is missing`)
  const { width, height } = value
  if (typeof width !== 'number' || typeof height !== 'number' || width < 1 || height < 1) {
    throw new DesignParseError(`${where} needs a positive width and height`)
  }
  return { width, height }
}

function readElement(value: unknown, index: number): DesignElement {
  if (!isObject(value)) throw new DesignParseError(`elements[${index}] is not an object`)
  const label = typeof value.id === 'string' ? `"${value.id}"` : `elements[${index}]`
  if (typeof value.id !== 'string') throw new DesignParseError(`${label} has no string id`)
  if (typeof value.type !== 'string' || !TYPES.has(value.type)) {
    throw new DesignParseError(`${label} has unknown type ${JSON.stringify(value.type)}`)
  }
  for (const key of ['x', 'y', 'width', 'height']) {
    if (typeof value[key] !== 'number' || !Number.isFinite(value[key])) {
      throw new DesignParseError(`${label} needs a numeric ${key}`)
    }
  }
  const required: Record<string, string[]> = {
    text: ['content', 'font_family', 'font_size', 'color'],
    image: ['asset_id'],
    shape: ['shape_type', 'fill_color'],
  }
  for (const key of required[value.type]) {
    if (value[key] === undefined) throw new DesignParseError(`${label} (${value.type}) is missing ${key}`)
  }
  return value as DesignElement
}

export function readDesign(value: unknown, where = 'design'): Design {
  if (!isObject(value)) throw new DesignParseError(`${where} is not an object`)
  const canvas = readCanvas(value.canvas, `${where}.canvas`)
  if (!Array.isArray(value.elements) || value.elements.length === 0) {
    throw new DesignParseError(`${where}.elements must be a non-empty array`)
  }
  return { canvas, elements: value.elements.map(readElement) }
}

export type Parsed =
  | { kind: 'task'; task: DesignTask }
  | { kind: 'design'; design: Design }

/** Accepts either a task envelope ({source, target_canvas}) or a bare design. */
export function parseDesignJson(text: string): Parsed {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch (err) {
    throw new DesignParseError(`Not valid JSON: ${(err as Error).message}`)
  }
  if (isObject(raw) && 'source' in raw) {
    const source = readDesign(raw.source, 'source')
    const target = raw.target_canvas ? readCanvas(raw.target_canvas, 'target_canvas') : source.canvas
    return { kind: 'task', task: { ...(raw as object), source, target_canvas: target } as DesignTask }
  }
  return { kind: 'design', design: readDesign(raw) }
}

/** A design is a result for `source` when it carries exactly the same element ids. */
export function sharesIds(a: Design, b: Design): boolean {
  if (a.elements.length !== b.elements.length) return false
  const ids = new Set(a.elements.map((e) => e.id))
  return b.elements.every((e) => ids.has(e.id))
}

export function sortedByZ(elements: DesignElement[]): DesignElement[] {
  return elements
    .map((el, i) => ({ el, i }))
    .sort((a, b) => (a.el.z_index ?? 0) - (b.el.z_index ?? 0) || a.i - b.i)
    .map(({ el }) => el)
}

// ---------------------------------------------------------------------------
// Colour helpers: the UI borrows its accent from the loaded design.
// ---------------------------------------------------------------------------

export interface Rgba {
  r: number
  g: number
  b: number
  a: number
}

export function parseColor(value: unknown): Rgba | null {
  if (typeof value !== 'string') return null
  const s = value.trim()
  const fn = s.match(/^rgba?\(([^)]+)\)$/i)
  if (fn) {
    const [r, g, b, a = '1'] = fn[1].split(',').map((p) => p.trim())
    const out = { r: Number(r), g: Number(g), b: Number(b), a: Number(a) }
    return [out.r, out.g, out.b, out.a].every(Number.isFinite) ? out : null
  }
  const hex = s.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i)
  if (hex) {
    const h = hex[1].length === 3 ? [...hex[1]].map((c) => c + c).join('') : hex[1]
    return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: 1 }
  }
  return null
}

function hsl({ r, g, b }: Rgba) {
  const [rn, gn, bn] = [r / 255, g / 255, b / 255]
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  const l = (max + min) / 2
  const d = max - min
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1))
  return { s, l }
}

/** Distinct, vivid colours used in the design, most prominent first. */
export function designPalette(design: Design): string[] {
  const weight = new Map<string, number>()
  const add = (value: unknown, area: number) => {
    const c = parseColor(value)
    if (!c || c.a < 0.5) return
    const { s, l } = hsl(c)
    if (s < 0.35 || l < 0.25 || l > 0.85) return
    const key = `rgb(${Math.round(c.r)}, ${Math.round(c.g)}, ${Math.round(c.b)})`
    weight.set(key, (weight.get(key) ?? 0) + Math.sqrt(Math.max(area, 1)) * (0.5 + s))
  }
  for (const el of design.elements) {
    const area = el.width * el.height
    if (el.type === 'shape') add(el.fill_color, area)
    if (el.type === 'text') {
      add(el.color, area * 0.5)
      for (const run of el.style_runs ?? []) add(run.color, area)
    }
  }
  return [...weight.entries()].sort((a, b) => b[1] - a[1]).map(([k]) => k)
}

export function aspectLabel({ width, height }: Canvas): string {
  const ratio = width / height
  const known: [number, string][] = [
    [1, '1:1'], [4 / 5, '4:5'], [9 / 16, '9:16'], [16 / 9, '16:9'], [2 / 3, '2:3'],
    [3 / 2, '3:2'], [4 / 3, '4:3'], [3 / 4, '3:4'], [4, '4:1'], [1.91, '1.91:1'],
  ]
  for (const [value, label] of known) if (Math.abs(ratio - value) / value < 0.01) return label
  return ratio >= 1 ? `${ratio.toFixed(2)}:1` : `1:${(1 / ratio).toFixed(2)}`
}
