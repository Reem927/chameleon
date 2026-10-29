import { memo, useSyncExternalStore, type CSSProperties, type ReactNode } from 'react'
import { motion, type Transition } from 'motion/react'
import type { Design, DesignElement, ImageElement, ShapeElement, TextElement } from '../../types/contracts'
import { sortedByZ } from './design'
import { assetUrl, assetsVersion, subscribeAssets } from './sources'

interface Props {
  design: Design
  scale: number
  /** Tag used by element threads to find the same element in another pane. */
  pane?: string
  hoveredId?: string | null
  onHover?: (id: string | null) => void
  /** Stagger elements so a design change reads as a morph. */
  morph?: boolean
  className?: string
  children?: ReactNode
}

const spring: Transition = { type: 'spring', stiffness: 170, damping: 24, mass: 0.9 }

const FAMILY_FALLBACK: Record<string, string> = {
  serif: 'Georgia, serif',
  sans: 'system-ui, sans-serif',
}

function fontStack(family: string) {
  const generic = /serif/i.test(family) && !/sans/i.test(family) ? FAMILY_FALLBACK.serif : FAMILY_FALLBACK.sans
  return `"${family}", ${generic}`
}

function TextBody({ el, scale }: { el: TextElement; scale: number }) {
  const runs = [...(el.style_runs ?? [])].sort((a, b) => a.start - b.start)
  const parts: ReactNode[] = []
  let cursor = 0
  runs.forEach((run, i) => {
    const start = Math.max(cursor, run.start)
    const end = Math.min(el.content.length, run.end)
    if (start > cursor) parts.push(el.content.slice(cursor, start))
    if (end > start) {
      parts.push(
        <span
          key={i}
          style={{
            color: run.color,
            fontWeight: run.font_weight ? (run.font_weight === 'bold' ? 700 : 400) : undefined,
            fontStyle: run.font_style,
          }}
        >
          {el.content.slice(start, end)}
        </span>,
      )
      cursor = end
    }
  })
  if (cursor < el.content.length) parts.push(el.content.slice(cursor))

  return (
    <motion.div
      className="dc-text"
      initial={false}
      animate={{ fontSize: el.font_size * scale, letterSpacing: (el.letter_spacing ?? 0) * scale }}
      transition={spring}
      style={{
        fontFamily: fontStack(el.font_family),
        fontWeight: el.font_weight === 'bold' ? 700 : 400,
        fontStyle: el.font_style === 'italic' ? 'italic' : 'normal',
        color: el.color,
        textAlign: el.text_align ?? 'left',
        lineHeight: el.line_height ?? 1.2,
      }}
    >
      {parts}
    </motion.div>
  )
}

function ImageBody({ el }: { el: ImageElement }) {
  useSyncExternalStore(subscribeAssets, assetsVersion)
  const url = assetUrl(el.asset_id)
  if (!url) {
    return (
      <div className="dc-missing" title={`Missing asset: ${el.asset_id}`}>
        <span>missing</span>
        <code>{el.asset_id}</code>
      </div>
    )
  }
  return <img className="dc-img" src={url} alt="" draggable={false} style={{ objectFit: el.fit ?? 'contain' }} />
}

function shapeStyle(el: ShapeElement, scale: number): CSSProperties {
  if (el.shape_type === 'line') {
    const stroke = Math.max(1, el.stroke_width ?? 1) * scale
    return {
      position: 'absolute',
      left: 0,
      right: 0,
      top: `calc(50% - ${stroke / 2}px)`,
      height: stroke,
      background: el.stroke_color ?? el.fill_color,
    }
  }
  const radius =
    el.shape_type === 'ellipse' ? '50%' : Math.min(el.corner_radius ?? 0, el.width / 2, el.height / 2) * scale
  return { position: 'absolute', inset: 0, background: el.fill_color, borderRadius: radius }
}

const Element = memo(function Element({
  el,
  order,
  scale,
  morph,
  highlighted,
  dimmed,
  onHover,
}: {
  el: DesignElement
  order: number
  scale: number
  morph: boolean
  highlighted: boolean
  dimmed: boolean
  onHover?: (id: string | null) => void
}) {
  return (
    <motion.div
      className={`dc-el dc-${el.type}${highlighted ? ' is-hot' : ''}${dimmed ? ' is-dim' : ''}`}
      data-el-id={el.id}
      initial={false}
      animate={{
        left: el.x * scale,
        top: el.y * scale,
        width: el.width * scale,
        height: el.height * scale,
        rotate: el.rotation ?? 0,
      }}
      transition={morph ? { ...spring, delay: Math.min(order * 0.018, 0.3) } : { duration: 0 }}
      style={{ zIndex: el.z_index ?? 0, opacity: el.opacity ?? 1 }}
      onPointerEnter={onHover ? () => onHover(el.id) : undefined}
      onPointerLeave={onHover ? () => onHover(null) : undefined}
    >
      {el.type === 'text' && <TextBody el={el} scale={scale} />}
      {el.type === 'image' && <ImageBody el={el} />}
      {el.type === 'shape' && <div style={shapeStyle(el, scale)} />}
    </motion.div>
  )
})

/**
 * Live DOM approximation of a design. Browser text wrapping is not the
 * official renderer's, so this is labelled "approximate" wherever it is shown.
 */
export function DesignCanvas({ design, scale, pane, hoveredId, onHover, morph = false, className, children }: Props) {
  const elements = sortedByZ(design.elements)
  return (
    <motion.div
      className={`dc-canvas${className ? ` ${className}` : ''}`}
      data-pane={pane}
      initial={false}
      animate={{ width: design.canvas.width * scale, height: design.canvas.height * scale }}
      transition={morph ? spring : { duration: 0 }}
    >
      {elements.map((el, i) => (
        <Element
          key={el.id}
          el={el}
          order={i}
          scale={scale}
          morph={morph}
          highlighted={hoveredId === el.id}
          dimmed={!!hoveredId && hoveredId !== el.id}
          onHover={onHover}
        />
      ))}
      {children}
    </motion.div>
  )
}
