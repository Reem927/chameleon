import { describe, expect, it } from 'vitest'
import type { Design } from '../types/contracts'
import { runChecks } from '../features/inspector/checks'
import { parseDesignJson } from '../features/preview/design'
import { readSample, sampleFiles } from './realSamples'

const tasks = sampleFiles.map((file) => {
  const parsed = parseDesignJson(readSample(file))
  if (parsed.kind !== 'task') throw new Error(`${file} is not a task`)
  return { file, source: parsed.task.source }
})

const clone = (d: Design): Design => structuredClone(d)
const status = (checks: ReturnType<typeof runChecks>, key: string) => checks.find((c) => c.key === key)?.status
const anyAsset = () => true

describe.each(tasks)('rule checks on $file', ({ source }) => {
  // Bounds is left out: some official sources deliberately bleed decorations
  // past their own canvas, which an output is not allowed to do.
  it('passes the structural rules when the design comes back unchanged', () => {
    const checks = runChecks(source, clone(source), source.canvas, anyAsset)
    for (const key of ['ids', 'canvas', 'fields', 'ratio']) expect(status(checks, key)).toBe('pass')
  })

  it('passes bounds once every element is pulled inside the canvas', () => {
    const out = clone(source)
    for (const el of out.elements) {
      el.rotation = 0
      el.width = Math.min(el.width, out.canvas.width)
      el.height = Math.min(el.height, out.canvas.height)
      el.x = Math.min(Math.max(0, el.x), out.canvas.width - el.width)
      el.y = Math.min(Math.max(0, el.y), out.canvas.height - el.height)
    }
    expect(status(runChecks(source, out, out.canvas, anyAsset), 'bounds')).toBe('pass')
  })

  it('fails IDs when an element is dropped', () => {
    const out = clone(source)
    const dropped = out.elements.pop()!
    const ids = runChecks(source, out, source.canvas, anyAsset).find((c) => c.key === 'ids')!
    expect(ids.status).toBe('fail')
    expect(ids.ids).toContain(dropped.id)
  })

  it('fails bounds when an element is pushed off the canvas', () => {
    const out = clone(source)
    out.elements[0].x = source.canvas.width + 10
    expect(status(runChecks(source, out, source.canvas, anyAsset), 'bounds')).toBe('fail')
  })

  it('fails locked fields when anything beyond geometry changes', () => {
    const out = clone(source)
    out.elements[0].z_index = (out.elements[0].z_index ?? 0) + 1
    expect(status(runChecks(source, out, source.canvas, anyAsset), 'fields')).toBe('fail')
  })

  it('reports the requested canvas when the output size differs', () => {
    const target = { width: source.canvas.width + 1, height: source.canvas.height }
    expect(status(runChecks(source, clone(source), target, anyAsset), 'canvas')).toBe('fail')
  })
})

describe('image proportions', () => {
  const withImage = tasks.find((t) => t.source.elements.some((e) => e.type === 'image' && e.fit !== 'cover'))!
  const firstContain = (d: Design) => d.elements.find((e) => e.type === 'image' && e.fit !== 'cover')!

  it('fails a contain image stretched past 5%', () => {
    const out = clone(withImage.source)
    const img = firstContain(out)
    img.width *= 1.2
    const ratio = runChecks(withImage.source, out, out.canvas, anyAsset).find((c) => c.key === 'ratio')!
    expect(ratio.status).toBe('fail')
    expect(ratio.ids).toContain(img.id)
  })

  it('allows a 4% drift', () => {
    const out = clone(withImage.source)
    firstContain(out).width *= 1.04
    expect(status(runChecks(withImage.source, out, out.canvas, anyAsset), 'ratio')).toBe('pass')
  })
})

describe('missing assets', () => {
  it('warns for every image whose asset is not available', () => {
    const { source } = tasks.find((t) => t.source.elements.some((e) => e.type === 'image'))!
    const images = source.elements.filter((e) => e.type === 'image')
    const assets = runChecks(source, clone(source), source.canvas, () => false).find((c) => c.key === 'assets')!
    expect(assets.status).toBe('warn')
    expect(assets.ids).toEqual(images.map((e) => e.id))
  })
})
