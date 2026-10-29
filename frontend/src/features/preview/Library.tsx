import { useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import type { Design } from '../../types/contracts'
import { DesignCanvas } from './DesignCanvas'
import { parseDesignJson } from './design'
import { ingestFiles, loadSample } from './ingest'
import { samples, type SampleRef } from './sources'
import { useApp } from './store'

interface Thumb {
  sample: SampleRef
  design: Design | null
  label: string
}

function useSampleThumbs(): Thumb[] {
  const [thumbs, setThumbs] = useState<Thumb[]>(() =>
    samples.map((sample) => ({ sample, design: null, label: sample.file })),
  )
  useEffect(() => {
    let alive = true
    Promise.all(
      samples.map(async (sample) => {
        try {
          const parsed = parseDesignJson(await sample.load())
          if (parsed.kind === 'task') {
            return { sample, design: parsed.task.source, label: parsed.task.difficulty_label ?? sample.file }
          }
          return { sample, design: parsed.design, label: sample.file }
        } catch {
          return { sample, design: null, label: sample.file }
        }
      }),
    ).then((next) => alive && setThumbs(next))
    return () => {
      alive = false
    }
  }, [])
  return thumbs
}

export function FilePicker({ children, className }: { children: React.ReactNode; className?: string }) {
  const input = useRef<HTMLInputElement>(null)
  return (
    <>
      <button type="button" className={className} onClick={() => input.current?.click()}>
        {children}
      </button>
      <input
        ref={input}
        type="file"
        hidden
        multiple
        accept=".json,application/json,image/*"
        onChange={(e) => {
          if (e.target.files) ingestFiles(e.target.files)
          e.target.value = ''
        }}
      />
    </>
  )
}

export function SampleGallery({ variant }: { variant: 'hero' | 'rail' }) {
  const thumbs = useSampleThumbs()
  const active = useApp((s) => s.source?.sampleFile)
  const box = variant === 'hero' ? 168 : 76

  if (!thumbs.length) {
    return <p className="muted">No samples found in input/. Drop or paste a design JSON instead.</p>
  }

  return (
    <div className={`gallery gallery-${variant}`}>
      {thumbs.map((t, i) => {
        const scale = t.design ? box / Math.max(t.design.canvas.width, t.design.canvas.height) : 0
        return (
          <motion.button
            key={t.sample.file}
            type="button"
            className={`sample-card${active === t.sample.file ? ' is-active' : ''}`}
            onClick={() => loadSample(t.sample)}
            initial={variant === 'hero' ? { opacity: 0, y: 24, rotate: (i - 1) * 3 } : false}
            animate={{ opacity: 1, y: 0, rotate: variant === 'hero' ? (i - 1) * 2 : 0 }}
            whileHover={{ y: -6, rotate: 0, scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 260, damping: 22, delay: variant === 'hero' ? 0.15 + i * 0.08 : 0 }}
          >
            <span className="sample-thumb" style={{ width: box, height: box }}>
              {t.design && <DesignCanvas design={t.design} scale={scale} />}
            </span>
            <span className="sample-meta">
              <strong>{t.label}</strong>
              {t.design && (
                <span className="mono muted">
                  {t.design.canvas.width}×{t.design.canvas.height} · {t.design.elements.length} el
                </span>
              )}
            </span>
          </motion.button>
        )
      })}
    </div>
  )
}
