// Typed client for the demo API (docs/api-contract.md). The UI picks this
// module up automatically (features/preview/engine.ts); Vite proxies /api to
// the Python server on 127.0.0.1:8000.
import type { ResizeRequest, ResizeResponse } from '../types/contracts'

const API = '/api'

export async function resize(request: ResizeRequest, signal?: AbortSignal): Promise<ResizeResponse> {
  const response = await fetch(`${API}/resize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    const message = detail && typeof detail.error === 'string' ? detail.error : response.statusText
    throw new Error(`resize failed (${response.status}): ${message}`)
  }
  return (await response.json()) as ResizeResponse
}

export async function health(signal?: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch(`${API}/health`, { signal })
    if (!response.ok) return false
    const body = (await response.json()) as { status?: unknown }
    return body.status === 'ok'
  } catch (error) {
    // A cancelled check is the caller's decision, not an offline engine.
    if (signal?.aborted) throw error
    return false
  }
}
