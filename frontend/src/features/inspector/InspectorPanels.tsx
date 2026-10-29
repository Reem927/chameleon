import { useMemo, useSyncExternalStore } from 'react'
import { motion } from 'motion/react'
import type { CandidateScore, DebugPayload, DesignElement } from '../../types/contracts'
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

function candidates(debug: DebugPayload): CandidateScore[] {
  if (Array.isArray(debug.candidate_scores)) return debug.candidate_scores
  return Object.entries(debug.candidate_scores).map(([name, v]) =>
    typeof v === 'number' ? { name, total: v } : { name, ...(v as Omit<CandidateScore, 'name'>) },
  )
}

/** Candidate strategies from Reem's DebugPayload. Hidden until the API returns one. */
export function DecisionPanel() {
  const debug = useApp((s) => s.result?.debug)
  if (!debug) return null
  const list = candidates(debug).sort((a, b) => (b.total ?? 0) - (a.total ?? 0))
  const best = Math.max(...list.map((c) => c.total ?? 0), 1e-9)

  return (
    <div className="panel decision-panel">
      <header className="panel-head">
        <h2>Decision</h2>
        <span className="chip">{debug.strategy}</span>
      </header>
      <ul className="candidates">
        {list.map((c, i) => (
          <li key={c.name} className={`candidate${c.name === debug.strategy ? ' is-chosen' : ''}${c.legal === false ? ' is-illegal' : ''}`}>
            <span className="cand-name">{c.name}</span>
            <span className="cand-bar">
              <motion.span
                initial={{ width: 0 }}
                animate={{ width: `${((c.total ?? 0) / best) * 100}%` }}
                transition={{ delay: i * 0.05, type: 'spring', stiffness: 90, damping: 18 }}
              />
            </span>
            <span className="mono">{c.total?.toFixed(3) ?? '—'}</span>
          </li>
        ))}
      </ul>
      {debug.warnings.length > 0 && (
        <ul className="warnings">
          {debug.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
