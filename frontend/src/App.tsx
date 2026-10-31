import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, MotionConfig, motion } from 'motion/react'
import { Mascot, type MascotMood } from './components/Mascot'
import { Kbd, Segmented, Toasts } from './components/ui'
import { TargetPanel } from './features/canvas-controls/TargetPanel'
import { DecisionPanel } from './features/inspector/DecisionPanel'
import { ChecksPanel, LayersPanel } from './features/inspector/InspectorPanels'
import { copyJson, downloadJson, downloadUrl } from './features/preview/exporters'
import { ingestFiles, ingestJson } from './features/preview/ingest'
import { FilePicker, SampleGallery } from './features/preview/Library'
import { Stage } from './features/preview/Stage'
import { sameCanvas, useApp, type ViewMode } from './features/preview/store'
import { useSkin } from './features/preview/useSkin'

const RESIZE_DEBOUNCE_MS = 380
const ENGINE_RETRY_MS = 8000

function Wordmark() {
  return (
    <span className="wordmark" aria-label="Chameleon">
      {'Chameleon'.split('').map((ch, i) => (
        <span key={i} style={{ animationDelay: `${i * 90}ms` }}>
          {ch}
        </span>
      ))}
    </span>
  )
}

function EnginePill() {
  const { engine, resizing, checkEngine } = useApp()
  const label = resizing ? 'reshaping…' : engine === 'online' ? 'engine online' : engine === 'checking' ? 'checking engine' : 'engine offline'
  return (
    <button
      type="button"
      className={`engine-pill is-${resizing ? 'busy' : engine}`}
      onClick={() => checkEngine()}
      title={
        engine === 'offline'
          ? 'Start the API with python -m api.app. Until then results come from output/ or dropped files. Retrying every few seconds.'
          : 'Click to re-check'
      }
    >
      <span className="pulse" aria-hidden />
      {label}
    </button>
  )
}

function ResultActions() {
  const { result, source, toast } = useApp()
  if (!result || !source) return null
  const stem = `${source.label}_${result.design.canvas.width}x${result.design.canvas.height}`
  return (
    <div className="result-actions">
      <button
        type="button"
        onClick={() =>
          copyJson(result.design).then(
            () => toast('good', 'Result JSON copied'),
            () => toast('bad', 'Clipboard is blocked here'),
          )
        }
      >
        Copy JSON
      </button>
      <button type="button" onClick={() => downloadJson(result.design, `${stem}.json`)}>
        JSON ↓
      </button>
      <button type="button" disabled={!result.pngUrl} onClick={() => result.pngUrl && downloadUrl(result.pngUrl, `${stem}.png`)}>
        PNG ↓
      </button>
    </div>
  )
}

function StageBar() {
  const { source, result, target, showing, setShowing, engine, resizing, error } = useApp()
  if (!source) return null
  const stale = !result || !sameCanvas(result.design.canvas, target)
  let message: string
  if (resizing) message = 'The engine is reshaping your design…'
  else if (error && stale)
    message = result
      ? `Resize failed, so this is still the ${result.design.canvas.width}×${result.design.canvas.height} result. Change the size to try again.`
      : 'Resize failed. Change the size to try again.'
  else if (!result && engine !== 'online') message = 'Engine offline. Start it with python -m api.app, or drop an output JSON.'
  else if (stale && engine !== 'online') message = `Showing the ${result!.design.canvas.width}×${result!.design.canvas.height} result. Engine offline, so the new target can't be resized yet.`
  else if (showing === 'source' && engine === 'online') message = 'Drag the frame or pick a preset. The engine reshapes live.'
  else if (showing === 'source') message = 'Showing the source. Press Space to shift.'
  else message = 'Showing the result. Hover any element to trace it.'

  return (
    <div className="stage-bar">
      <div className="flip" role="group" aria-label="Show source or result">
        <button type="button" className={showing === 'source' ? 'is-on' : ''} onClick={() => setShowing('source')}>
          Source
        </button>
        <motion.button
          type="button"
          className={`shift-btn${showing === 'result' ? ' is-on' : ''}`}
          disabled={!result}
          onClick={() => setShowing(showing === 'result' ? 'source' : 'result')}
          whileTap={{ scale: 0.94 }}
        >
          Shift <Kbd>Space</Kbd>
        </motion.button>
        <button type="button" className={showing === 'result' ? 'is-on' : ''} disabled={!result} onClick={() => setShowing('result')}>
          Result
        </button>
      </div>
      <AnimatePresence mode="wait">
        <motion.p key={message} className="stage-msg" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}>
          {message}
        </motion.p>
      </AnimatePresence>
      <span className="approx">Live preview is approximate · official PNG in Render check</span>
    </div>
  )
}

function Hero() {
  return (
    <motion.section className="hero" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }}>
      <Mascot size={96} />
      <h1>
        One design.
        <br />
        <span className="hero-shift">Every shape.</span>
      </h1>
      <p className="hero-sub">Drop a design JSON, paste one, or pick a sample. Then drag the frame and watch it adapt.</p>
      <SampleGallery variant="hero" />
      <div className="hero-actions">
        <FilePicker className="btn-primary">Open files…</FilePicker>
        <span className="muted">
          or <Kbd>Ctrl</Kbd>+<Kbd>V</Kbd> a JSON · drop images to add assets
        </span>
      </div>
    </motion.section>
  )
}

export default function App() {
  const { source, result, target, engine, resizing, error, view, setView, toasts, dismissToast, checkEngine, requestResize } = useApp()
  const [dragOver, setDragOver] = useState(false)
  const [dragging, setDragging] = useState(false)
  const dragDepth = useRef(0)
  const [celebrate, setCelebrate] = useState(false)

  useSkin(source?.design)

  useEffect(() => {
    checkEngine()
  }, [checkEngine])

  // Keep looking for the API while it is down, so starting it later just works.
  useEffect(() => {
    if (engine !== 'offline') return
    const timer = setInterval(checkEngine, ENGINE_RETRY_MS)
    return () => clearInterval(timer)
  }, [engine, checkEngine])

  // Ask the engine for a new layout once the target settles. Results read
  // from output/ may be from an older engine, so a live one replaces them.
  useEffect(() => {
    if (!source || engine !== 'online' || dragging) return
    if (result && result.origin !== 'engine-run' && sameCanvas(result.design.canvas, target)) return
    const timer = setTimeout(requestResize, RESIZE_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [source, target, engine, dragging, result, requestResize])

  // A fresh result gets a little celebration from the mascot.
  useEffect(() => {
    if (!result) return
    setCelebrate(true)
    const t = setTimeout(() => setCelebrate(false), 1400)
    return () => clearTimeout(t)
  }, [result])

  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      if ((e.target as HTMLElement).closest('input, textarea')) return
      if (e.clipboardData?.files.length) return void ingestFiles(e.clipboardData.files)
      const text = e.clipboardData?.getData('text')
      if (text?.trim().startsWith('{')) ingestJson(text, 'pasted design')
    }
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input, textarea') || e.metaKey || e.ctrlKey || e.altKey) return
      const s = useApp.getState()
      if (e.code === 'Space' && s.result) {
        e.preventDefault()
        s.setShowing(s.showing === 'result' ? 'source' : 'result')
      }
      const modes: Record<string, ViewMode> = { '1': 'morph', '2': 'split', '3': 'render' }
      if (modes[e.key] && s.source) s.setView(modes[e.key])
    }
    window.addEventListener('paste', onPaste)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('paste', onPaste)
      window.removeEventListener('keydown', onKey)
    }
  }, [])

  const mood: MascotMood = resizing ? 'busy' : error ? 'sad' : celebrate ? 'happy' : 'idle'

  return (
    <MotionConfig reducedMotion="user">
      <div
        className={`app${resizing ? ' is-busy' : ''}`}
        onDragEnter={(e) => {
          if (!e.dataTransfer.types.includes('Files')) return
          dragDepth.current++
          setDragOver(true)
        }}
        onDragLeave={() => {
          dragDepth.current = Math.max(0, dragDepth.current - 1)
          if (!dragDepth.current) setDragOver(false)
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          dragDepth.current = 0
          setDragOver(false)
          ingestFiles(e.dataTransfer.files)
        }}
      >
        <div className="ambient" aria-hidden />
        <header className="topbar">
          <div className="brand">
            <Mascot mood={mood} size={34} />
            <Wordmark />
          </div>
          {source && (
            <>
              <div className="source-chip" title={source.meta?.notes}>
                <span className="muted">source</span> <b>{source.label}</b>
                <span className="mono muted">
                  {source.design.canvas.width}×{source.design.canvas.height}
                </span>
              </div>
              <Segmented
                label="View"
                value={view}
                onChange={setView}
                options={[
                  { value: 'morph', label: 'Morph', hint: 'Animate source into result (1)' },
                  { value: 'split', label: 'Split', hint: 'Side by side with element threads (2)' },
                  { value: 'render', label: 'Render check', hint: 'Live preview vs official PNG (3)' },
                ]}
              />
            </>
          )}
          <div className="topbar-end">
            <EnginePill />
            {source && <FilePicker className="ghost-btn">Open…</FilePicker>}
          </div>
        </header>

        <AnimatePresence mode="wait">
          {!source ? (
            <Hero key="hero" />
          ) : (
            <motion.main key="work" className="workspace" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <aside className="rail rail-left">
                <div className="panel">
                  <header className="panel-head">
                    <h2>Samples</h2>
                  </header>
                  <SampleGallery variant="rail" />
                </div>
                <LayersPanel />
              </aside>
              <div className="center">
                <Stage onDragState={setDragging} />
                <StageBar />
              </div>
              <aside className="rail rail-right">
                <TargetPanel />
                <ChecksPanel />
                <DecisionPanel />
                <ResultActions />
              </aside>
            </motion.main>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {dragOver && (
            <motion.div className="drop-veil" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <motion.div className="drop-card" initial={{ scale: 0.9 }} animate={{ scale: 1 }}>
                <Mascot mood="happy" size={72} />
                <p>Drop design JSON, output JSON, official PNG or assets</p>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        <Toasts items={toasts} onDismiss={dismissToast} />
      </div>
    </MotionConfig>
  )
}
