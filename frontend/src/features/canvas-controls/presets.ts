import type { Canvas } from '../../types/contracts'

export interface Preset extends Canvas {
  name: string
  group: string
}

// Presets are optional: they come from src/mocks/dev-presets/ when that folder
// exists. Without it this list is empty and the UI hides the preset chips.
const modules = import.meta.glob('../../mocks/dev-presets/*.ts', { eager: true, import: 'default' }) as Record<
  string,
  Preset[]
>

export const presets: Preset[] = Object.values(modules).flat()

export function presetFor(canvas: Canvas): Preset | undefined {
  return presets.find((p) => p.width === canvas.width && p.height === canvas.height)
}

/** Nearest preset within `tolerance` design px on both sides, for drag snapping. */
export function snapToPreset(canvas: Canvas, tolerance: number): Preset | undefined {
  let best: Preset | undefined
  let bestDist = Infinity
  for (const p of presets) {
    const dw = Math.abs(p.width - canvas.width)
    const dh = Math.abs(p.height - canvas.height)
    if (dw > tolerance || dh > tolerance) continue
    const dist = Math.hypot(dw, dh)
    if (dist < bestDist) {
      best = p
      bestDist = dist
    }
  }
  return best
}
