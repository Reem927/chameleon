import type { Design } from '../../types/contracts'

function save(href: string, name: string) {
  const a = document.createElement('a')
  a.href = href
  a.download = name
  a.click()
}

export function downloadJson(design: Design, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(design, null, 2)], { type: 'application/json' }))
  save(url, name)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function downloadUrl(url: string, name: string) {
  save(url, name)
}

export async function copyJson(design: Design) {
  await navigator.clipboard.writeText(JSON.stringify(design, null, 2))
}
