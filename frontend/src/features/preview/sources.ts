// Read-only links to real repo files. Nothing here is authored data: Vite
// resolves these globs against input/, output/ and brand_kit/ at dev/build time,
// and an empty folder simply yields an empty list.

const sampleFiles = import.meta.glob('../../../../input/*.json', { query: '?raw', import: 'default' }) as Record<
  string,
  () => Promise<string>
>

// Engine outputs written by `python -m engine.main` (gitignored, may be absent).
const outputJsonFiles = import.meta.glob('../../../../output/*_output.json', {
  query: '?raw',
  import: 'default',
}) as Record<string, () => Promise<string>>

const outputPngFiles = import.meta.glob('../../../../output/*_output.png', {
  query: '?url',
  import: 'default',
  eager: true,
}) as Record<string, string>

const brandAssets = import.meta.glob('../../../../brand_kit/assets/*.{png,jpg,jpeg,webp,svg}', {
  query: '?url',
  import: 'default',
  eager: true,
}) as Record<string, string>

const baseName = (path: string) => path.split('/').pop() ?? path

export interface SampleRef {
  file: string
  load: () => Promise<string>
}

export const samples: SampleRef[] = Object.entries(sampleFiles)
  .map(([path, load]) => ({ file: baseName(path), load }))
  .sort((a, b) => a.file.localeCompare(b.file))

/** Engine output for a sample file name, if `engine.main` has been run. */
export function findEngineOutput(sampleFile: string): { load: () => Promise<string>; pngUrl: string | null } | null {
  const stem = sampleFile.replace(/\.json$/i, '')
  const jsonEntry = Object.entries(outputJsonFiles).find(([path]) => baseName(path) === `${stem}_output.json`)
  if (!jsonEntry) return null
  const pngEntry = Object.entries(outputPngFiles).find(([path]) => baseName(path) === `${stem}_output.png`)
  return { load: jsonEntry[1], pngUrl: pngEntry?.[1] ?? null }
}

const assetUrls = new Map<string, string>(Object.entries(brandAssets).map(([path, url]) => [baseName(path), url]))
const listeners = new Set<() => void>()
let version = 0

export function assetUrl(assetId: string): string | null {
  return assetUrls.get(assetId) ?? null
}

/** Images the user drops in join the brand kit assets, matched by file name. */
export function registerUploadedAsset(file: File) {
  const previous = assetUrls.get(file.name)
  if (previous?.startsWith('blob:')) URL.revokeObjectURL(previous)
  assetUrls.set(file.name, URL.createObjectURL(file))
  version++
  listeners.forEach((fn) => fn())
}

export function subscribeAssets(fn: () => void) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export const assetsVersion = () => version
