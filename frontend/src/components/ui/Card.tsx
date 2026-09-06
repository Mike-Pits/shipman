import type { ReactNode } from 'react'
import './Card.css'

export default function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`card${className ? ` ${className}` : ''}`}>{children}</div>
}
