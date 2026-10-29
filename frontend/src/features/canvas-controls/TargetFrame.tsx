import { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { Canvas } from '../../types/contracts'
import { aspectLabel } from '../preview/design'
import { presetFor, snapToPreset } from './presets'

type Edge = 'e' | 's' | 'se' | 'w' | 'n' | 'nw' | 'ne' | 'sw'

const SNAP_SCREEN_PX = 14
const MIN_SIDE = 16
const MAX_SIDE = 8000

interface Props {
  target: Canvas
  scale: number
  /** True when the displayed canvas already is the target (frame hugs it). */
  hugging: boolean
  onDrag(next: Canvas): void
  onDragState(dragging: boolean): void
}

/**
 * Drag-to-resize frame for the target canvas. The frame is centred on the
 * stage, so moving an edge by d screen px grows that side by 2d.
 * Shift keeps the aspect ratio; edges snap to presets when one is near.
 */
export function TargetFrame({ target, scale, hugging, onDrag, onDragState }: Props) {
  const start = useRef<{ x: number; y: number; canvas: Canvas; edge: Edge } | null>(null)
  const [dragging, setDragging] = useState(false)
  const [snapped, setSnapped] = useState<string | null>(null)

  const onPointerDown = (edge: Edge) => (e: React.PointerEvent) => {
    e.preventDefault()
    e.stopPropagation()
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
    start.current = { x: e.clientX, y: e.clientY, canvas: target, edge }
    setDragging(true)
    onDragState(true)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    const s = start.current
    if (!s) return
    const sx = s.edge.includes('e') ? 1 : s.edge.includes('w') ? -1 : 0
    const sy = s.edge.includes('s') ? 1 : s.edge.includes('n') ? -1 : 0
    let width = s.canvas.width + (sx * 2 * (e.clientX - s.x)) / scale
    let height = s.canvas.height + (sy * 2 * (e.clientY - s.y)) / scale
    if (e.shiftKey) {
      const ratio = s.canvas.width / s.canvas.height
      if (sx && sy) height = width / ratio
      else if (sx) height = width / ratio
      else width = height * ratio
    }
    width = Math.min(MAX_SIDE, Math.max(MIN_SIDE, Math.round(width)))
    height = Math.min(MAX_SIDE, Math.max(MIN_SIDE, Math.round(height)))
    const snap = e.altKey ? undefined : snapToPreset({ width, height }, SNAP_SCREEN_PX / scale)
    setSnapped(snap?.name ?? null)
    onDrag(snap ? { width: snap.width, height: snap.height } : { width, height })
  }

  const onPointerUp = () => {
    if (!start.current) return
    start.current = null
    setDragging(false)
    setSnapped(null)
    onDragState(false)
  }

  const named = snapped ?? presetFor(target)?.name
  const handles: Edge[] = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw']

  return (
    <motion.div
      className={`target-frame${hugging ? ' is-hugging' : ''}${dragging ? ' is-dragging' : ''}`}
      initial={false}
      animate={{ width: target.width * scale, height: target.height * scale }}
      transition={dragging ? { duration: 0 } : { type: 'spring', stiffness: 220, damping: 28 }}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      {handles.map((h) => (
        <span
          key={h}
          className={`tf-handle tf-${h}`}
          onPointerDown={onPointerDown(h)}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          aria-hidden
        />
      ))}
      <div className="tf-readout">
        <span className="mono">
          {target.width} × {target.height}
        </span>
        <span className="tf-aspect">{aspectLabel(target)}</span>
        <AnimatePresence mode="popLayout">
          {named && (
            <motion.span
              key={named}
              className={`tf-name${snapped ? ' is-snap' : ''}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
            >
              {named}
            </motion.span>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
