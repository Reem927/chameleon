import { beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach } from 'vitest'
import { TargetPanel } from '../features/canvas-controls/TargetPanel'
import { presets, snapToPreset } from '../features/canvas-controls/presets'
import { parseDesignJson } from '../features/preview/design'
import { useApp } from '../features/preview/store'
import { readSample, sampleFiles } from './realSamples'

beforeEach(() => {
  const parsed = parseDesignJson(readSample(sampleFiles[0]))
  if (parsed.kind !== 'task') throw new Error('expected a task')
  useApp.getState().loadSource({ label: 'sample', design: parsed.task.source }, parsed.task.target_canvas)
})
afterEach(cleanup)

describe('target panel', () => {
  it('commits a typed width on Enter', async () => {
    render(<TargetPanel />)
    const width = screen.getByLabelText('Target width')
    await userEvent.clear(width)
    await userEvent.type(width, '777{Enter}')
    expect(useApp.getState().target.width).toBe(777)
  })

  it('ignores non-numeric typing and restores on blur', async () => {
    const before = useApp.getState().target.height
    render(<TargetPanel />)
    const height = screen.getByLabelText('Target height')
    await userEvent.clear(height)
    await userEvent.type(height, 'abc')
    await userEvent.tab()
    expect(useApp.getState().target.height).toBe(before)
  })

  it('swaps width and height', async () => {
    const { width, height } = useApp.getState().target
    render(<TargetPanel />)
    await userEvent.click(screen.getByLabelText('Swap width and height'))
    expect(useApp.getState().target).toEqual({ width: height, height: width })
  })

  it('steps with arrow keys, ×10 with Shift', async () => {
    const start = useApp.getState().target.width
    render(<TargetPanel />)
    screen.getByLabelText('Target width').focus()
    await userEvent.keyboard('{ArrowUp}{Shift>}{ArrowUp}{/Shift}')
    expect(useApp.getState().target.width).toBe(start + 11)
  })
})

describe.runIf(presets.length > 0)('presets (dev-presets folder present)', () => {
  it('applies a preset on click', async () => {
    render(<TargetPanel />)
    const p = presets[0]
    await userEvent.click(screen.getByRole('button', { name: new RegExp(p.name) }))
    expect(useApp.getState().target).toEqual({ width: p.width, height: p.height })
  })

  it('snaps only inside the tolerance', () => {
    const p = presets[0]
    expect(snapToPreset({ width: p.width + 3, height: p.height - 3 }, 5)?.name).toBe(p.name)
    expect(snapToPreset({ width: p.width + 30, height: p.height }, 5)?.name).not.toBe(p.name)
  })
})
