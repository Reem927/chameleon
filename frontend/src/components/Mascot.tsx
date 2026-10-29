import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'

export type MascotMood = 'idle' | 'busy' | 'happy' | 'sad'

/** The chameleon: takes its colour from the loaded design and follows the pointer. */
export function Mascot({ mood = 'idle', size = 56 }: { mood?: MascotMood; size?: number }) {
  const ref = useRef<SVGSVGElement>(null)
  const [look, setLook] = useState({ x: 0, y: 0 })
  const reduce = useReducedMotion()

  useEffect(() => {
    if (reduce) return
    const onMove = (e: PointerEvent) => {
      const box = ref.current?.getBoundingClientRect()
      if (!box) return
      // Eye centre sits at (82, 32) in a 120×80 viewBox.
      const ex = box.left + (82 / 120) * box.width
      const ey = box.top + (32 / 80) * box.height
      const angle = Math.atan2(e.clientY - ey, e.clientX - ex)
      const reach = Math.min(1, Math.hypot(e.clientX - ex, e.clientY - ey) / 240)
      setLook({ x: Math.cos(angle) * 3.4 * reach, y: Math.sin(angle) * 3.4 * reach })
    }
    window.addEventListener('pointermove', onMove)
    return () => window.removeEventListener('pointermove', onMove)
  }, [reduce])

  const busy = mood === 'busy' && !reduce
  return (
    <svg
      ref={ref}
      className={`mascot mascot-${mood}`}
      viewBox="0 0 120 80"
      width={size * 1.5}
      height={size}
      role="img"
      aria-label={`Chameleon mascot, ${mood}`}
    >
      <motion.g
        animate={busy ? { rotate: [0, -4, 0] } : reduce ? undefined : { y: [0, -1.2, 0] }}
        transition={{ duration: busy ? 0.7 : 3.2, repeat: Infinity, ease: 'easeInOut' }}
        style={{ originX: '60px', originY: '50px' }}
      >
        <motion.path
          d="M26 54 C10 56 3 66 9 73 C15 79 27 74 23 66 C21 61 14 63 16 68"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="6"
          strokeLinecap="round"
          animate={busy ? { rotate: [0, 14, 0] } : undefined}
          transition={{ duration: 0.7, repeat: Infinity }}
          style={{ originX: '26px', originY: '54px' }}
        />
        <path d="M44 58 l-5 14 h7 M70 58 l4 14 h7" stroke="var(--accent-deep)" strokeWidth="5" strokeLinecap="round" fill="none" />
        <path
          d="M20 50 C20 30 38 18 60 19 C76 20 88 26 95 34 L108 40 C112 42 111 48 105 48 L94 49 C88 59 74 62 58 62 C40 62 22 60 20 50 Z"
          fill="var(--accent)"
        />
        <path d="M34 24 l4 -8 l4 7 l5 -9 l4 8 l5 -8 l4 9" fill="none" stroke="var(--accent-deep)" strokeWidth="3" strokeLinejoin="round" />
        <circle cx="44" cy="40" r="3.2" fill="var(--accent-deep)" opacity="0.55" />
        <circle cx="56" cy="47" r="2.4" fill="var(--accent-deep)" opacity="0.45" />
        <circle cx="62" cy="34" r="2.8" fill="var(--accent-deep)" opacity="0.5" />
        <circle cx="82" cy="32" r="10" fill="var(--accent-2)" />
        <circle cx="82" cy="32" r="7" fill="#fff" />
        <motion.circle
          cx="82"
          cy="32"
          r={mood === 'sad' ? 2.6 : 3.6}
          fill="#16121c"
          animate={{ cx: 82 + look.x, cy: 32 + look.y }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        />
        {mood === 'happy' && (
          <motion.path
            d="M108 45 C118 45 120 52 114 54"
            fill="none"
            stroke="#ff6f91"
            strokeWidth="2.6"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: [0, 1, 0] }}
            transition={{ duration: 0.9 }}
          />
        )}
      </motion.g>
    </svg>
  )
}
