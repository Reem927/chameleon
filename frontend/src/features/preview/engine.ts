import type { ResizeClient } from '../../types/contracts'

// Reem owns the typed API client in src/services/. Until that module exists the
// glob is empty and the UI runs in "engine offline" mode; once it lands it is
// picked up without any change here.
const serviceModules = import.meta.glob('../../services/index.ts') as Record<
  string,
  () => Promise<Partial<ResizeClient>>
>

let clientPromise: Promise<ResizeClient | null> | null = null

export function loadEngineClient(): Promise<ResizeClient | null> {
  clientPromise ??= (async () => {
    const load = Object.values(serviceModules)[0]
    if (!load) return null
    const mod = await load()
    if (typeof mod.resize !== 'function' || typeof mod.health !== 'function') {
      console.warn('src/services/index.ts must export resize() and health(); see types/contracts.ts ResizeClient')
      return null
    }
    return mod as ResizeClient
  })()
  return clientPromise
}
