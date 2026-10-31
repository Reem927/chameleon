import { create } from 'zustand'
import type { Canvas, DebugPayload, Design, DesignTask, ResizeClient } from '../../types/contracts'
import { loadEngineClient } from './engine'

export type ResultOrigin = 'api' | 'engine-run' | 'file'
export type ViewMode = 'morph' | 'split' | 'render'
export type EngineState = 'checking' | 'online' | 'offline'

export interface SourceState {
  label: string
  design: Design
  meta?: Omit<DesignTask, 'source' | 'target_canvas'>
  sampleFile?: string
}

export interface ResultState {
  design: Design
  pngUrl: string | null
  origin: ResultOrigin
  debug: DebugPayload | null
}

export interface Toast {
  id: number
  tone: 'info' | 'good' | 'bad'
  text: string
}

interface AppState {
  source: SourceState | null
  target: Canvas
  result: ResultState | null
  engine: EngineState
  resizing: boolean
  error: string | null
  view: ViewMode
  showing: 'source' | 'result'
  hoveredId: string | null
  toasts: Toast[]

  loadSource(source: SourceState, target: Canvas): void
  setTarget(target: Canvas): void
  setResult(result: ResultState): void
  clearResult(): void
  setView(view: ViewMode): void
  setShowing(showing: 'source' | 'result'): void
  setHovered(id: string | null): void
  toast(tone: Toast['tone'], text: string): void
  dismissToast(id: number): void
  checkEngine(): Promise<void>
  requestResize(): Promise<void>
}

let client: ResizeClient | null = null
let inflight: AbortController | null = null
let toastId = 0

export const sameCanvas = (a: Canvas, b: Canvas) => a.width === b.width && a.height === b.height

export const useApp = create<AppState>((set, get) => ({
  source: null,
  target: { width: 1080, height: 1080 },
  result: null,
  engine: 'checking',
  resizing: false,
  error: null,
  view: 'morph',
  showing: 'source',
  hoveredId: null,
  toasts: [],

  loadSource(source, target) {
    inflight?.abort()
    set({ source, target, result: null, error: null, resizing: false, showing: 'source', hoveredId: null })
  },
  setTarget(target) {
    const width = Math.max(1, Math.round(target.width))
    const height = Math.max(1, Math.round(target.height))
    set({ target: { width, height }, error: null })
  },
  setResult(result) {
    set({ result, error: null })
  },
  clearResult() {
    set({ result: null, showing: 'source' })
  },
  setView(view) {
    set({ view })
  },
  setShowing(showing) {
    set({ showing })
  },
  setHovered(hoveredId) {
    if (get().hoveredId !== hoveredId) set({ hoveredId })
  },
  toast(tone, text) {
    const id = ++toastId
    set((s) => ({ toasts: [...s.toasts.slice(-3), { id, tone, text }] }))
    setTimeout(() => get().dismissToast(id), 4200)
  },
  dismissToast(id) {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
  },

  async checkEngine() {
    // Background retries stay quiet; only the first check shows "checking".
    if (get().engine !== 'offline') set({ engine: 'checking' })
    client = await loadEngineClient()
    if (!client) return set({ engine: 'offline' })
    try {
      set({ engine: (await client.health()) ? 'online' : 'offline' })
    } catch {
      set({ engine: 'offline' })
    }
  },

  async requestResize() {
    const { source, target, engine } = get()
    if (!source || !client || engine !== 'online') return
    inflight?.abort()
    const controller = new AbortController()
    inflight = controller
    set({ resizing: true, error: null })
    try {
      const res = await client.resize({ source: source.design, target_canvas: target }, controller.signal)
      if (controller.signal.aborted) return
      set({
        result: { design: res.design, pngUrl: res.preview_url, origin: 'api', debug: res.debug },
        resizing: false,
        showing: 'result',
      })
    } catch (err) {
      if (controller.signal.aborted) return
      // A dead server and a rejected design look alike from here; ask health.
      // Going offline starts the retry loop, and coming back re-requests.
      const alive = await client.health().catch(() => false)
      if (!alive) {
        set({ resizing: false, error: null, engine: 'offline' })
        get().toast('bad', 'Lost the engine. Reconnecting when it is back…')
        return
      }
      const message = err instanceof Error ? err.message : String(err)
      set({ resizing: false, error: message })
      get().toast('bad', `Resize failed: ${message}`)
    }
  },
}))
