import { useEffect } from 'react'
import type { Design } from '../../types/contracts'
import { designPalette } from './design'

/** The app shell takes on the loaded design's own vivid colours. */
export function useSkin(design: Design | null | undefined) {
  useEffect(() => {
    const root = document.documentElement
    const palette = design ? designPalette(design) : []
    if (palette[0]) root.style.setProperty('--accent', palette[0])
    else root.style.removeProperty('--accent')
    if (palette[1]) root.style.setProperty('--accent-2', palette[1])
    else root.style.removeProperty('--accent-2')
  }, [design])
}
