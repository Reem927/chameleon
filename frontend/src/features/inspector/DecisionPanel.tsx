import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import type { CandidateScore } from '../../types/contracts'
import { useApp } from '../preview/store'

const AXIS_LABEL: Record<string, string> = {
  collision: 'Collision',
  text: 'Text',
  hierarchy: 'Hierarchy',
  canvas_use: 'Canvas use',
  alignment: 'Alignment',
  balance_spacing: 'Spacing',
  group_cohesion: 'Groups',
  reading_order: 'Reading',
  similarity: 'Similarity',
  source_alignment: 'Src align',
  area_share: 'Area share',
}

const axisLabel = (key: string) => AXIS_LABEL[key] ?? key.replace(/_/g, ' ')

/** `compact_banner@0.6+clean` → family "compact banner" plus tags. */
export function describeCandidate(name: string) {
  const clean = name.endsWith('+clean')
  const base = clean ? name.slice(0, -'+clean'.length) : name
  const [family, ratio] = base.split('@')
  const tags = [ratio && `${Math.round(Number(ratio) * 100)}% graphics`, clean && 'cleaned'].filter(Boolean) as string[]
  return { family: family.replace(/_/g, ' '), tags }
}

const SIZE = 240
const CENTER = SIZE / 2
const RADIUS = 78

function point(i: number, n: number, value: number) {
  const angle = (Math.PI * 2 * i) / n - Math.PI / 2
  const r = RADIUS * Math.max(0, Math.min(1, value))
  return [CENTER + Math.cos(angle) * r, CENTER + Math.sin(angle) * r] as const
}

function shape(axes: string[], breakdown: Record<string, number>) {
  return axes.map((k, i) => point(i, axes.length, breakdown[k] ?? 0).map((v) => v.toFixed(1)).join(',')).join(' ')
}

/** Radar of every score part: the chosen layout filled, a focused one outlined on top. */
function Radar({ axes, chosen, focus }: { axes: string[]; chosen: CandidateScore; focus: CandidateScore | null }) {
  const n = axes.length
  return (
    <svg className="radar" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Score parts of the chosen layout">
      {[0.25, 0.5, 0.75, 1].map((ring) => (
        <polygon key={ring} className="radar-ring" points={axes.map((_, i) => point(i, n, ring).join(',')).join(' ')} />
      ))}
      {axes.map((key, i) => {
        const [x, y] = point(i, n, 1)
        const [lx, ly] = point(i, n, 1.24)
        return (
          <g key={key}>
            <line className="radar-spoke" x1={CENTER} y1={CENTER} x2={x} y2={y} />
            <text className="radar-label" x={lx} y={ly} textAnchor={Math.abs(lx - CENTER) < 6 ? 'middle' : lx > CENTER ? 'start' : 'end'} dominantBaseline="middle">
              {axisLabel(key)}
            </text>
          </g>
        )
      })}
      <motion.polygon
        className="radar-chosen"
        initial={false}
        animate={{ points: shape(axes, chosen.breakdown ?? {}) }}
        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
      />
      <AnimatePresence>
        {focus && focus.name !== chosen.name && focus.breakdown && (
          <motion.polygon
            key="focus"
            className="radar-focus"
            initial={{ opacity: 0, points: shape(axes, chosen.breakdown ?? {}) }}
            animate={{ opacity: 1, points: shape(axes, focus.breakdown) }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 160, damping: 20 }}
          />
        )}
      </AnimatePresence>
    </svg>
  )
}

/** Why the engine picked its layout: every candidate, its score parts, and the policy hints. */
export function DecisionPanel() {
  const debug = useApp((s) => s.result?.debug)
  const [focusName, setFocusName] = useState<string | null>(null)
  if (!debug || !Array.isArray(debug.candidate_scores)) return null

  const rows = [...debug.candidate_scores].sort(
    (a, b) => Number(b.legal) - Number(a.legal) || (b.total ?? 0) - (a.total ?? 0),
  )
  const chosen = rows.find((c) => c.name === debug.strategy) ?? rows.find((c) => c.legal)
  const focus = rows.find((c) => c.name === focusName) ?? null
  const legal = rows.filter((c) => c.legal)
  const totals = legal.map((c) => c.total ?? 0)
  const low = Math.min(...totals)
  const high = Math.max(...totals)
  const axes = chosen?.breakdown ? Object.keys(chosen.breakdown) : []
  const label = describeCandidate(debug.strategy)

  return (
    <div className="panel decision-panel">
      <header className="panel-head">
        <h2>Decision</h2>
        <span className="chip mono">
          {legal.length}/{rows.length} legal
        </span>
      </header>
      <p className="decision-pick">
        <span className="muted">Picked</span> <b>{label.family}</b>
        {label.tags.map((t) => (
          <span key={t} className="tag">
            {t}
          </span>
        ))}
      </p>
      {chosen && axes.length > 2 && <Radar axes={axes} chosen={chosen} focus={focus} />}
      {focus && focus.name !== chosen?.name && (
        <p className="hint radar-legend">
          <span className="swatch swatch-chosen" /> picked <span className="swatch swatch-focus" /> {[describeCandidate(focus.name).family, ...describeCandidate(focus.name).tags].join(' · ')}
        </p>
      )}
      <ul className="candidates" onPointerLeave={() => setFocusName(null)}>
        {rows.map((c, i) => {
          const d = describeCandidate(c.name)
          const width = c.legal && high > low ? 0.15 + (0.85 * ((c.total ?? 0) - low)) / (high - low) : c.legal ? 1 : 0
          return (
            <li
              key={c.name}
              className={`candidate${c.name === chosen?.name ? ' is-chosen' : ''}${c.legal ? '' : ' is-illegal'}${c.name === focusName ? ' is-focus' : ''}`}
              onPointerEnter={() => setFocusName(c.name)}
              title={c.problems?.join('\n')}
            >
              <span className="cand-name">
                {d.family}
                {d.tags.length > 0 && <small> · {d.tags.join(' · ')}</small>}
              </span>
              {c.legal ? (
                <>
                  <span className="cand-bar">
                    <motion.span
                      initial={{ width: 0 }}
                      animate={{ width: `${width * 100}%` }}
                      transition={{ delay: i * 0.03, type: 'spring', stiffness: 90, damping: 18 }}
                    />
                  </span>
                  <span className="mono cand-total">{(c.total ?? 0).toFixed(3)}</span>
                </>
              ) : (
                <span className="cand-problem">{c.problems?.[0] ?? 'illegal'}</span>
              )}
            </li>
          )
        })}
      </ul>
      {debug.policies.length > 0 && (
        <div className="policies">
          <h3>Policy hints</h3>
          {debug.policies.map((p) => (
            <p key={p.strategy}>
              <b>{describeCandidate(p.strategy).family}</b> {p.reason}
            </p>
          ))}
        </div>
      )}
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
