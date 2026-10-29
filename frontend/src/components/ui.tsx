import { AnimatePresence, motion } from 'motion/react'
import type { ReactNode } from 'react'

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T
  options: { value: T; label: ReactNode; hint?: string; disabled?: boolean }[]
  onChange: (value: T) => void
  label: string
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          title={o.hint}
          disabled={o.disabled}
          className={value === o.value ? 'is-on' : undefined}
          onClick={() => onChange(o.value)}
        >
          {value === o.value && (
            <motion.span layoutId={`seg-${label}`} className="segmented-pill" transition={{ type: 'spring', stiffness: 400, damping: 32 }} />
          )}
          <span className="segmented-label">{o.label}</span>
        </button>
      ))}
    </div>
  )
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="kbd">{children}</kbd>
}

export interface ToastItem {
  id: number
  tone: 'info' | 'good' | 'bad'
  text: string
}

export function Toasts({ items, onDismiss }: { items: ToastItem[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toasts" aria-live="polite">
      <AnimatePresence initial={false}>
        {items.map((t) => (
          <motion.button
            key={t.id}
            layout
            type="button"
            className={`toast toast-${t.tone}`}
            initial={{ opacity: 0, y: 24, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40, transition: { duration: 0.18 } }}
            onClick={() => onDismiss(t.id)}
          >
            {t.text}
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  )
}
