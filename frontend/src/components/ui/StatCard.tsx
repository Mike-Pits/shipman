import type { ReactNode } from 'react'
import Card from './Card'
import './Card.css'

export default function StatCard({
  label,
  value,
  tone,
  sub,
}: {
  label: string
  value: ReactNode
  tone?: 'success' | 'warning' | 'danger'
  sub?: ReactNode
}) {
  return (
    <Card className="stat-card">
      <span className="stat-card-label">{label}</span>
      <span className={`stat-card-value${tone ? ` tone-${tone}` : ''}`}>{value}</span>
      {sub && <span className="stat-card-sub">{sub}</span>}
    </Card>
  )
}
