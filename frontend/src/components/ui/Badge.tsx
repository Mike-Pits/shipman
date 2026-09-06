import type { ReactNode } from 'react'
import './Badge.css'

export type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral' | 'info'

export default function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}
