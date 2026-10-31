import { useMemo, useSyncExternalStore } from 'react'
import { motion } from 'motion/react'
import type { DesignElement } from '../../types/contracts'
import { sortedByZ } from '../preview/design'
import { assetUrl, assetsVersion, subscribeAssets } from '../preview/sources'
import { sameCanvas, useApp } from '../preview/store'
import { runChecks, type Check } from './checks'

const ORIGIN_LABEL = {
  api: 'live engine',
  'engine-run': 'engine run in output/',
  file: 'dropped file',
} as const

function ScoreRing({ passed, total }: { passed: number; total: number }) {
  const r = 17
  const c = 2 * Math.PI * r
  const ratio = total ? passed / total : 0
  return (
    <svg className="score-ring" viewBox="0 0 44 44" width="44" height="44" aria-label={`${passed} of ${total} checks pass`}>
      <circle cx="22" cy="22" r={r} className="ring-track" />
      <motion.circle
        cx="22"
        cy="22"
        r={r}
        className="ring-fill"
        strokeDasharray={c}
        initial={{ strokeDashoffset: c }}
        animate={{ strokeDashoffset: c * (1 - ratio) }}
        transition={{ type: 'spring', stiffness: 80, damping: 18 }}
      />
      <text x="22" y="26" textAnchor="middle" className="mono">
        {passed}/{total}
      </text>
    </svg>
  )
}

export function ChecksPanel() {
  const { source, result, target, setHovered } = useApp()
  const version = useSyncExternalStore(subscribeAssets, assetsVersion)

  const checks = useMemo<Check[]>(() => {
    if (!source || !result) return []
    return runChecks(source.design, result.design, target, (id) => assetUrl(id) !== null)
    // `version` re-runs the asset check after the user drops images in.
  }, [source, result, target, version])

  if (!source) return null
  const stale = result && !sameCanvas(result.design.canvas, target)
  const passed = checks.filter((c) => c.status === 'pass').length

  return (
    <div className="panel checks-panel">
      <header className="panel-head">
        <h2>Rule checks</h2>
        {result && <ScoreRing passed={passed} total={checks.length} />}
      </header>
      {!result ? (
        <p className="hint">Checks appear once there is a result: from the engine, an output/ run, or a dropped output JSON.</p>
      ) : (
        <>
          <p className="hint">
            Result from {ORIGIN_LABEL[result.origin]}
            {stale && <b className="warn-text"> · target has changed since</b>}
          </p>
          <ul className="checks">
            {checks.map((c, i) => (
              <motion.li
                key={c.key}
                className={`check check-${c.status}`}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                onPointerEnter={() => c.ids?.length && setHovered(c.ids[0])}
                onPointerLeave={() => setHovered(null)}
                title={c.detail}
              >
                <span className="check-dot" aria-hidden />
                <span className="check-label">{c.label}</span>
                <span className="check-value mono">{c.value}</span>
                {c.detail && <span className="check-detail">{c.detail}</span>}
              </motion.li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function delta(src: DesignElement | undefined, out: DesignElement | undefined): string | null {
  if (!src || !out) return null
  if (src.type === 'text' && out.type === 'text' && src.font_size !== out.font_size) {
    return `${+src.font_size.toFixed(1)}→${+out.font_size.toFixed(1)}px`
  }
  const scale = Math.sqrt((out.width * out.height) / Math.max(1, src.width * src.height))
  return Math.abs(scale - 1) > 0.01 ? `${scale > 1 ? '+' : ''}${Math.round((scale - 1) * 100)}%` : null
}

const TYPE_GLYPH = { text: 'T', image: '▣', shape: '◆' } as const

export function LayersPanel() {
  const { source, result, hoveredId, setHovered } = useApp()
  if (!source) return null
  const outById = new Map(result?.design.elements.map((e) => [e.id, e]))
  const layers = sortedByZ(source.design.elements).reverse()

  return (
    <div className="panel layers-panel">
      <header className="panel-head">
        <h2>Layers</h2>
        <span className="chip mono">{layers.length}</span>
      </header>
      <ul className="layers" onPointerLeave={() => setHovered(null)}>
        {layers.map((el) => {
          const d = delta(el, outById.get(el.id))
          return (
            <li
              key={el.id}
              className={`layer${hoveredId === el.id ? ' is-hot' : ''}`}
              onPointerEnter={() => setHovered(el.id)}
            >
              <span className={`layer-type t-${el.type}`}>{TYPE_GLYPH[el.type]}</span>
              <span className="layer-id">{el.id}</span>
              {el.group_id && <span className="layer-group">{el.group_id}</span>}
              {d && <span className="layer-delta mono">{d}</span>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
