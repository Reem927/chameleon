import { MUTABLE_FIELDS, type Canvas, type Design, type DesignElement } from '../../types/contracts'

export type CheckStatus = 'pass' | 'warn' | 'fail'

export interface Check {
  key: string
  label: string
  status: CheckStatus
  value: string
  detail?: string
  /** Element ids this check is about, for highlighting. */
  ids?: string[]
}

export const IMAGE_RATIO_LIMIT = 0.05
const EDGE_TOLERANCE = 0.5
const SMALL_FONT_PX = 8

/** Axis-aligned bounds of an element after rotation about its centre. */
export function rotatedBounds(el: DesignElement) {
  const theta = ((el.rotation ?? 0) * Math.PI) / 180
  const cos = Math.abs(Math.cos(theta))
  const sin = Math.abs(Math.sin(theta))
  const w = el.width * cos + el.height * sin
  const h = el.width * sin + el.height * cos
  const cx = el.x + el.width / 2
  const cy = el.y + el.height / 2
  return { left: cx - w / 2, top: cy - h / 2, right: cx + w / 2, bottom: cy + h / 2 }
}

const MUTABLE = new Set<string>(MUTABLE_FIELDS)
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b)
const pct = (n: number) => `${(n * 100).toFixed(1)}%`
const list = (ids: string[], max = 4) => ids.slice(0, max).join(', ') + (ids.length > max ? ` +${ids.length - max}` : '')

/**
 * Hard-rule checks computed from the real source and output designs.
 * Mirrors the structural rules in RULES.md; it is a local aid, not Adobe's scorer.
 */
export function runChecks(
  source: Design,
  output: Design,
  target: Canvas,
  hasAsset: (assetId: string) => boolean,
): Check[] {
  const checks: Check[] = []
  const sourceById = new Map(source.elements.map((e) => [e.id, e]))
  const outIds = output.elements.map((e) => e.id)
  const outSet = new Set(outIds)

  const missing = [...sourceById.keys()].filter((id) => !outSet.has(id))
  const added = [...outSet].filter((id) => !sourceById.has(id))
  const dupes = outIds.filter((id, i) => outIds.indexOf(id) !== i)
  const idProblems = [...missing, ...added, ...dupes]
  checks.push({
    key: 'ids',
    label: 'IDs preserved',
    status: idProblems.length ? 'fail' : 'pass',
    value: `${outSet.size - added.length}/${sourceById.size}`,
    detail: idProblems.length
      ? [
          missing.length && `missing ${list(missing)}`,
          added.length && `added ${list(added)}`,
          dupes.length && `duplicated ${list(dupes)}`,
        ]
          .filter(Boolean)
          .join(' · ')
      : 'Every element came back exactly once',
    ids: idProblems,
  })

  const sizeOk = output.canvas.width === target.width && output.canvas.height === target.height
  checks.push({
    key: 'canvas',
    label: 'Target canvas',
    status: sizeOk ? 'pass' : 'fail',
    value: `${output.canvas.width}×${output.canvas.height}`,
    detail: sizeOk ? 'Matches the requested size' : `Requested ${target.width}×${target.height}`,
  })

  const changed: string[] = []
  const changedFields = new Set<string>()
  for (const el of output.elements) {
    const src = sourceById.get(el.id)
    if (!src) continue
    const keys = new Set([...Object.keys(src), ...Object.keys(el)])
    for (const key of keys) {
      if (MUTABLE.has(key) && !(key === 'font_size' && src.type !== 'text')) continue
      if (!same(src[key], el[key])) {
        changed.push(el.id)
        changedFields.add(key)
      }
    }
  }
  const changedIds = [...new Set(changed)]
  checks.push({
    key: 'fields',
    label: 'Locked fields',
    status: changedIds.length ? 'fail' : 'pass',
    value: changedIds.length ? `${changedIds.length} changed` : 'untouched',
    detail: changedIds.length
      ? `${[...changedFields].join(', ')} changed on ${list(changedIds)}`
      : 'Only x, y, width, height and font size moved',
    ids: changedIds,
  })

  const off = output.elements.filter((el) => {
    const b = rotatedBounds(el)
    return (
      b.left < -EDGE_TOLERANCE ||
      b.top < -EDGE_TOLERANCE ||
      b.right > output.canvas.width + EDGE_TOLERANCE ||
      b.bottom > output.canvas.height + EDGE_TOLERANCE
    )
  })
  checks.push({
    key: 'bounds',
    label: 'On canvas',
    status: off.length ? 'fail' : 'pass',
    value: off.length ? `${off.length} outside` : 'all inside',
    detail: off.length ? `Outside the canvas: ${list(off.map((e) => e.id))}` : 'Rotation-aware bounds, 0.5px tolerance',
    ids: off.map((e) => e.id),
  })

  let worst = 0
  let worstId: string | null = null
  const stretched: string[] = []
  for (const el of output.elements) {
    const src = sourceById.get(el.id)
    if (el.type !== 'image' || !src || el.fit === 'cover') continue
    if (!src.width || !src.height || !el.width || !el.height) continue
    const drift = Math.abs(el.width / el.height / (src.width / src.height) - 1)
    if (drift > worst) {
      worst = drift
      worstId = el.id
    }
    if (drift > IMAGE_RATIO_LIMIT) stretched.push(el.id)
  }
  checks.push({
    key: 'ratio',
    label: 'Image proportions',
    status: stretched.length ? 'fail' : 'pass',
    value: `${pct(worst)} / ${pct(IMAGE_RATIO_LIMIT)}`,
    detail: stretched.length
      ? `Stretched past the limit: ${list(stretched)}`
      : worstId
        ? `Largest drift on ${worstId}; cover images may crop freely`
        : 'No contain/fill images to check',
    ids: stretched,
  })

  const texts = output.elements.filter((e) => e.type === 'text')
  if (texts.length) {
    const smallest = texts.reduce((a, b) => (b.font_size < a.font_size ? b : a))
    const src = sourceById.get(smallest.id)
    const shrink = src?.type === 'text' ? smallest.font_size / src.font_size : 1
    checks.push({
      key: 'font',
      label: 'Smallest text',
      status: smallest.font_size < SMALL_FONT_PX ? 'warn' : 'pass',
      value: `${+smallest.font_size.toFixed(1)}px`,
      detail: `${smallest.id}, ${pct(shrink)} of its source size`,
      ids: [smallest.id],
    })
  }

  const absent = output.elements.filter((e) => e.type === 'image' && !hasAsset(e.asset_id))
  checks.push({
    key: 'assets',
    label: 'Assets found',
    status: absent.length ? 'warn' : 'pass',
    value: absent.length ? `${absent.length} missing` : 'all present',
    detail: absent.length
      ? `Renders as a placeholder: ${list(absent.map((e) => (e.type === 'image' ? e.asset_id : e.id)))}`
      : 'Every image asset resolved',
    ids: absent.map((e) => e.id),
  })

  return checks
}
