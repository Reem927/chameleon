import { beforeEach, describe, expect, it } from 'vitest'
import { DesignParseError, designPalette, parseDesignJson, sharesIds } from '../features/preview/design'
import { ingestJson } from '../features/preview/ingest'
import { useApp } from '../features/preview/store'
import { readSample, sampleFiles } from './realSamples'

describe.each(sampleFiles)('parsing %s', (file) => {
  const raw = JSON.parse(readSample(file))
  const parsed = parseDesignJson(readSample(file))

  it('reads the task envelope with its target canvas', () => {
    expect(parsed.kind).toBe('task')
    if (parsed.kind === 'task') expect(parsed.task.target_canvas).toEqual(raw.target_canvas)
  })

  it('keeps every element, including unknown keys, untouched', () => {
    if (parsed.kind === 'task') expect(parsed.task.source.elements).toEqual(raw.source.elements)
  })

  it('finds vivid colours for the UI skin', () => {
    if (parsed.kind === 'task') expect(designPalette(parsed.task.source).length).toBeGreaterThan(0)
  })
})

describe('invalid input', () => {
  const text = readSample(sampleFiles[0])
  const sample = JSON.parse(text)

  it('rejects text that is not JSON', () => {
    expect(() => parseDesignJson(text.slice(0, -5))).toThrow(DesignParseError)
  })

  it('names the element that lacks a required field', () => {
    const broken = structuredClone(sample)
    const el = broken.source.elements.find((e: { type: string }) => e.type === 'text')
    delete el.font_size
    expect(() => parseDesignJson(JSON.stringify(broken))).toThrow(new RegExp(`"${el.id}".*font_size`))
  })

  it('rejects a non-positive canvas', () => {
    const broken = structuredClone(sample)
    broken.source.canvas.width = 0
    expect(() => parseDesignJson(JSON.stringify(broken))).toThrow(/positive/)
  })
})

describe('routing dropped JSON', () => {
  beforeEach(() => useApp.setState({ source: null, result: null }))
  const text = readSample(sampleFiles[0])
  const raw = JSON.parse(text)

  it('loads a task as the source and adopts its target', () => {
    expect(ingestJson(text, 'sample')).toBe(true)
    const s = useApp.getState()
    expect(s.source?.design.canvas).toEqual(raw.source.canvas)
    expect(s.target).toEqual(raw.target_canvas)
  })

  it('pairs a same-id design at another size as the result', () => {
    ingestJson(text, 'sample')
    ingestJson(JSON.stringify({ ...raw.source, canvas: raw.target_canvas }), 'output')
    const s = useApp.getState()
    expect(s.result?.origin).toBe('file')
    expect(sharesIds(s.source!.design, s.result!.design)).toBe(true)
  })
})
