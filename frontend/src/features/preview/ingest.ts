import { DesignParseError, parseDesignJson, sharesIds } from './design'
import { findEngineOutput, registerUploadedAsset, type SampleRef } from './sources'
import { sameCanvas, useApp } from './store'

const fail = (err: unknown) => {
  const text = err instanceof DesignParseError ? err.message : `Could not read that: ${(err as Error).message}`
  useApp.getState().toast('bad', text)
}

/** Route one JSON text: a task, a fresh source design, or a result for the loaded source. */
export function ingestJson(text: string, label: string, sampleFile?: string): boolean {
  const app = useApp.getState()
  try {
    const parsed = parseDesignJson(text)
    if (parsed.kind === 'task') {
      const { source, target_canvas, ...meta } = parsed.task
      app.loadSource({ label, design: source, meta, sampleFile }, target_canvas)
      return true
    }
    const design = parsed.design
    if (app.source && sharesIds(app.source.design, design) && !sameCanvas(app.source.design.canvas, design.canvas)) {
      app.setTarget(design.canvas)
      app.setResult({ design, pngUrl: null, origin: 'file', debug: null })
      app.setShowing('result')
      app.toast('good', `${label} paired as the result for ${app.source.label}`)
      return true
    }
    app.loadSource({ label, design }, design.canvas)
    return true
  } catch (err) {
    fail(err)
    return false
  }
}

export async function loadSample(sample: SampleRef) {
  const ok = ingestJson(await sample.load(), sample.file.replace(/\.json$/i, ''), sample.file)
  if (!ok) return
  // With the live engine up, its fresh result beats an older output/ file.
  if (useApp.getState().engine === 'online') return
  const output = findEngineOutput(sample.file)
  if (!output) return
  try {
    const parsed = parseDesignJson(await output.load())
    const app = useApp.getState()
    if (parsed.kind !== 'design' || !app.source || !sharesIds(app.source.design, parsed.design)) return
    if (!sameCanvas(parsed.design.canvas, app.target)) return
    app.setResult({ design: parsed.design, pngUrl: output.pngUrl, origin: 'engine-run', debug: null })
  } catch {
    // A stale or half-written output file is not worth interrupting the user for.
  }
}

function imageSize(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
      URL.revokeObjectURL(url)
    }
    img.onerror = () => reject(new Error(`${file.name} is not a readable image`))
    img.src = url
  })
}

/**
 * Dropped/picked files. JSON first (so a source exists before its result),
 * then images: a PNG the size of the result canvas is treated as its official
 * render; anything else becomes an asset, matched to `asset_id` by file name.
 */
export async function ingestFiles(files: Iterable<File>) {
  const list = [...files]
  const json = list.filter((f) => f.name.toLowerCase().endsWith('.json') || f.type === 'application/json')
  const images = list.filter((f) => f.type.startsWith('image/'))
  const app = useApp.getState()

  json.sort((a, b) => Number(/_output/i.test(a.name)) - Number(/_output/i.test(b.name)))
  for (const file of json) ingestJson(await file.text(), file.name.replace(/\.json$/i, ''))

  for (const file of images) {
    try {
      const size = await imageSize(file)
      const result = useApp.getState().result
      if (result && size.width === result.design.canvas.width && size.height === result.design.canvas.height) {
        app.setResult({ ...result, pngUrl: URL.createObjectURL(file) })
        app.toast('good', `${file.name} attached as the official render`)
      } else {
        registerUploadedAsset(file)
        app.toast('info', `${file.name} added as an asset`)
      }
    } catch (err) {
      fail(err)
    }
  }
  if (!json.length && !images.length) app.toast('bad', 'Drop a design .json or image files')
}
