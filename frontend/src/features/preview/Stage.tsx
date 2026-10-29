import { useEffect, useRef, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { Canvas, Design } from '../../types/contracts'
import { useElementSize } from '../../components/useElementSize'
import { TargetFrame } from '../canvas-controls/TargetFrame'
import { DesignCanvas } from './DesignCanvas'
import { sameCanvas, useApp } from './store'

const PAD = 72

function fitScale(box: { width: number; height: number }, ...canvases: Canvas[]) {
  const w = Math.max(...canvases.map((c) => c.width))
  const h = Math.max(...canvases.map((c) => c.height))
  if (!box.width || !box.height) return 0
  return Math.min((box.width - PAD) / w, (box.height - PAD) / h, 4)
}

/** Shared pan/zoom surface: ctrl/⌘ + wheel zooms, drag empty space pans, double-click resets. */
function Viewport({ children, zoom, setZoom }: { children: ReactNode; zoom: number; setZoom: (z: number) => void }) {
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (zoom === 1) setPan({ x: 0, y: 0 })
  }, [zoom])

  useEffect(() => {
    const node = ref.current
    if (!node) return
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return
      e.preventDefault()
      setZoom(Math.min(8, Math.max(0.25, zoom * Math.exp(-e.deltaY * 0.0022))))
    }
    node.addEventListener('wheel', onWheel, { passive: false })
    return () => node.removeEventListener('wheel', onWheel)
  }, [zoom, setZoom])

  return (
    <div
      ref={ref}
      className="viewport"
      onPointerDown={(e) => {
        if ((e.target as HTMLElement).closest('.dc-canvas, .tf-handle, button, input, .render-stack')) return
        drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }
        e.currentTarget.setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        const d = drag.current
        if (d) setPan({ x: d.px + e.clientX - d.x, y: d.py + e.clientY - d.y })
      }}
      onPointerUp={() => (drag.current = null)}
      onDoubleClick={(e) => {
        if ((e.target as HTMLElement).closest('.dc-canvas, button, input')) return
        setZoom(1)
        setPan({ x: 0, y: 0 })
      }}
    >
      <div className="viewport-inner" style={{ transform: `translate(${pan.x}px, ${pan.y}px)` }}>
        {children}
      </div>
    </div>
  )
}

function MorphView({ zoom, onDragState }: { zoom: number; onDragState: (d: boolean) => void }) {
  const { source, result, target, showing, hoveredId, setHovered, setTarget } = useApp()
  const [ref, box] = useElementSize<HTMLDivElement>()
  const [frozen, setFrozen] = useState<number | null>(null)
  if (!source) return null

  const design: Design = showing === 'result' && result ? result.design : source.design
  const live = fitScale(box, design.canvas, target) * zoom
  const scale = frozen ?? live
  const hugging = sameCanvas(design.canvas, target)

  return (
    <div ref={ref} className="morph-view">
      {scale > 0 && (
        <div className="morph-center">
          <DesignCanvas design={design} scale={scale} morph pane="morph" hoveredId={hoveredId} onHover={setHovered} />
          <TargetFrame
            target={target}
            scale={scale}
            hugging={hugging}
            onDrag={setTarget}
            onDragState={(d) => {
              setFrozen(d ? live : null)
              onDragState(d)
            }}
          />
        </div>
      )}
    </div>
  )
}

/** Curved line joining the hovered element in the source pane to itself in the result pane. */
function Threads({ container }: { container: React.RefObject<HTMLDivElement | null> }) {
  const hoveredId = useApp((s) => s.hoveredId)
  const [path, setPath] = useState<string | null>(null)

  useEffect(() => {
    if (!hoveredId) return setPath(null)
    let frame = 0
    const tick = () => {
      const root = container.current
      const id = CSS.escape(hoveredId)
      const a = root?.querySelector(`[data-pane="src"] [data-el-id="${id}"]`)?.getBoundingClientRect()
      const b = root?.querySelector(`[data-pane="out"] [data-el-id="${id}"]`)?.getBoundingClientRect()
      const base = root?.getBoundingClientRect()
      if (a && b && base) {
        const ax = a.left + a.width / 2 - base.left
        const ay = a.top + a.height / 2 - base.top
        const bx = b.left + b.width / 2 - base.left
        const by = b.top + b.height / 2 - base.top
        const bend = Math.max(60, Math.abs(bx - ax) * 0.4)
        const horizontal = Math.abs(bx - ax) > Math.abs(by - ay)
        setPath(
          horizontal
            ? `M${ax},${ay} C${ax + bend},${ay} ${bx - bend},${by} ${bx},${by}`
            : `M${ax},${ay} C${ax},${ay + bend} ${bx},${by - bend} ${bx},${by}`,
        )
      }
      frame = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(frame)
  }, [hoveredId, container])

  return (
    <svg className="threads" aria-hidden>
      <AnimatePresence>
        {path && (
          <motion.g key={hoveredId} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <path d={path} className="thread-glow" />
            <motion.path d={path} className="thread-line" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.45 }} />
          </motion.g>
        )}
      </AnimatePresence>
    </svg>
  )
}

function SplitView({ zoom }: { zoom: number }) {
  const { source, result, hoveredId, setHovered } = useApp()
  const [ref, box] = useElementSize<HTMLDivElement>()
  if (!source) return null
  const out = result?.design
  // Each pane fits its own design (a 728×90 banner next to a 1080×1350 poster
  // would vanish at a shared scale). Pick the arrangement that shows more.
  const fitBoth = (pane: { width: number; height: number }) => {
    const s = fitScale(pane, source.design.canvas)
    const o = out ? fitScale(pane, out.canvas) : 0
    const area = s * s * source.design.canvas.width * source.design.canvas.height + (out ? o * o * out.canvas.width * out.canvas.height : 0)
    return { s, o, area }
  }
  const side = fitBoth({ width: (box.width - 24) / 2, height: box.height - 28 })
  const top = fitBoth({ width: box.width, height: (box.height - 52) / 2 })
  const stacked = top.area > side.area
  const chosen = stacked ? top : side
  const scale = chosen.s * zoom
  const outScale = chosen.o * zoom

  return (
    <div ref={ref} className={`split-view${stacked ? ' is-stacked' : ''}`}>
      <figure className="split-pane">
        <figcaption>Source · {source.design.canvas.width}×{source.design.canvas.height}</figcaption>
        {scale > 0 && <DesignCanvas design={source.design} scale={scale} pane="src" hoveredId={hoveredId} onHover={setHovered} />}
      </figure>
      <figure className="split-pane">
        <figcaption>{out ? `Result · ${out.canvas.width}×${out.canvas.height}` : 'Result · waiting for the engine'}</figcaption>
        {out && outScale > 0 ? (
          <DesignCanvas design={out} scale={outScale} pane="out" hoveredId={hoveredId} onHover={setHovered} />
        ) : (
          <div className="split-empty">No result yet</div>
        )}
      </figure>
      <Threads container={ref} />
    </div>
  )
}

function RenderView({ zoom }: { zoom: number }) {
  const result = useApp((s) => s.result)
  const [ref, box] = useElementSize<HTMLDivElement>()
  const [mode, setMode] = useState<'wipe' | 'onion'>('wipe')
  const [split, setSplit] = useState(0.5)
  // The measured div must always render, or the size observer never attaches.
  const scale = result ? fitScale({ width: box.width, height: box.height - 56 }, result.design.canvas) * zoom : 0
  const w = result ? result.design.canvas.width * scale : 0
  const h = result ? result.design.canvas.height * scale : 0

  return (
    <div ref={ref} className="render-view">
      {!result ? (
        <div className="render-empty">Load a result to compare it against the official render.</div>
      ) : !result.pngUrl ? (
        <div className="render-empty">
          No official render yet. Run <code>python -m engine.main</code>, or drop the PNG here.
        </div>
      ) : (
        scale > 0 && (
          <>
            <div className="render-stack" style={{ width: w, height: h }}>
              <img className="render-png" src={result.pngUrl} alt="Official cr-renderer output" />
              <div
                className="render-live"
                style={mode === 'wipe' ? { clipPath: `inset(0 ${(1 - split) * 100}% 0 0)` } : { opacity: split }}
              >
                <DesignCanvas design={result.design} scale={scale} />
              </div>
              {mode === 'wipe' && (
                <div className="wipe-bar" style={{ left: `${split * 100}%` }}>
                  <span>live</span>
                  <span>official</span>
                </div>
              )}
            </div>
            <div className="render-controls">
              <button type="button" className={mode === 'wipe' ? 'is-on' : ''} onClick={() => setMode('wipe')}>
                Wipe
              </button>
              <button type="button" className={mode === 'onion' ? 'is-on' : ''} onClick={() => setMode('onion')}>
                Onion skin
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.001}
                value={split}
                onChange={(e) => setSplit(Number(e.target.value))}
                aria-label={mode === 'wipe' ? 'Wipe position' : 'Live preview opacity'}
              />
            </div>
          </>
        )
      )}
    </div>
  )
}

export function Stage({ onDragState }: { onDragState: (d: boolean) => void }) {
  const view = useApp((s) => s.view)
  const [zoom, setZoom] = useState(1)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input, textarea')) return
      if (e.key === 'f' || e.key === 'F' || e.key === '0') setZoom(1)
      if (e.key === '+' || e.key === '=') setZoom((z) => Math.min(8, z * 1.25))
      if (e.key === '-') setZoom((z) => Math.max(0.25, z / 1.25))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <section className="stage" aria-label="Canvas stage">
      <Viewport zoom={zoom} setZoom={setZoom}>
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            className="stage-mode"
            initial={{ opacity: 0, scale: 0.985 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.01 }}
            transition={{ duration: 0.22 }}
          >
            {view === 'morph' && <MorphView zoom={zoom} onDragState={onDragState} />}
            {view === 'split' && <SplitView zoom={zoom} />}
            {view === 'render' && <RenderView zoom={zoom} />}
          </motion.div>
        </AnimatePresence>
      </Viewport>
      <div className="zoom-chip mono">
        <button type="button" onClick={() => setZoom(Math.max(0.25, zoom / 1.25))} aria-label="Zoom out">
          −
        </button>
        <button type="button" onClick={() => setZoom(1)} title="Fit (F)">
          {Math.round(zoom * 100)}%
        </button>
        <button type="button" onClick={() => setZoom(Math.min(8, zoom * 1.25))} aria-label="Zoom in">
          +
        </button>
      </div>
    </section>
  )
}
