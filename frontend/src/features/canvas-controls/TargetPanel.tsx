import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import type { Canvas } from '../../types/contracts'
import { aspectLabel } from '../preview/design'
import { useApp } from '../preview/store'
import { presets } from './presets'

function SizeInput({ label, value, onCommit }: { label: string; value: number; onCommit: (n: number) => void }) {
  const [draft, setDraft] = useState(String(value))
  useEffect(() => setDraft(String(value)), [value])
  const commit = () => {
    const n = Math.round(Number(draft))
    if (Number.isFinite(n) && n >= 1 && n <= 8000) onCommit(n)
    else setDraft(String(value))
  }
  return (
    <label className="size-input">
      <span>{label}</span>
      <input
        className="mono"
        inputMode="numeric"
        value={draft}
        aria-label={`Target ${label === 'W' ? 'width' : 'height'}`}
        onChange={(e) => setDraft(e.target.value.replace(/[^\d]/g, ''))}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') commit()
          if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            e.preventDefault()
            const step = (e.shiftKey ? 10 : 1) * (e.key === 'ArrowUp' ? 1 : -1)
            onCommit(Math.min(8000, Math.max(1, value + step)))
          }
        }}
      />
    </label>
  )
}

/** Tiny proportional rectangle so presets can be scanned by shape. */
function ShapeGlyph({ canvas }: { canvas: Canvas }) {
  const max = 18
  const s = max / Math.max(canvas.width, canvas.height)
  return (
    <span className="glyph" aria-hidden>
      <span style={{ width: Math.max(2, canvas.width * s), height: Math.max(2, canvas.height * s) }} />
    </span>
  )
}

export function TargetPanel() {
  const { target, setTarget, source } = useApp()
  const groups = [...new Set(presets.map((p) => p.group))]

  return (
    <div className="panel target-panel">
      <header className="panel-head">
        <h2>Target</h2>
        <span className="chip mono">{aspectLabel(target)}</span>
      </header>
      <div className="size-row">
        <SizeInput label="W" value={target.width} onCommit={(width) => setTarget({ ...target, width })} />
        <motion.button
          type="button"
          className="icon-btn"
          title="Swap width and height"
          aria-label="Swap width and height"
          whileTap={{ rotate: 180 }}
          onClick={() => setTarget({ width: target.height, height: target.width })}
        >
          ⇄
        </motion.button>
        <SizeInput label="H" value={target.height} onCommit={(height) => setTarget({ ...target, height })} />
      </div>
      {source && (
        <p className="hint">
          Drag the frame on the stage. <b>Shift</b> keeps ratio, <b>Alt</b> skips snapping.
        </p>
      )}
      {groups.map((group) => (
        <div key={group} className="preset-group">
          <h3>{group}</h3>
          <div className="preset-grid">
            {presets
              .filter((p) => p.group === group)
              .map((p) => {
                const on = p.width === target.width && p.height === target.height
                return (
                  <button
                    key={p.name}
                    type="button"
                    className={`preset${on ? ' is-on' : ''}`}
                    onClick={() => setTarget(p)}
                    title={`${p.width}×${p.height}`}
                  >
                    <ShapeGlyph canvas={p} />
                    <span>{p.name}</span>
                  </button>
                )
              })}
          </div>
        </div>
      ))}
    </div>
  )
}
