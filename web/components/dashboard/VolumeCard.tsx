'use client'

import type { DashboardVolumeWeek } from '@/lib/api/types'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

interface Props {
  history: DashboardVolumeWeek[]
}

export default function VolumeCard({ history }: Props) {
  return (
    <div style={{ margin: '12px 16px' }} className="sk-card">
      <div className="hand" style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>近8周训练量</div>

      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={history} barGap={2} barCategoryGap="25%">
          <CartesianGrid strokeDasharray="2 4" stroke="var(--rule-soft)" vertical={false} />
          <XAxis
            dataKey="week_label"
            tickLine={false}
            axisLine={false}
            tick={{ fontFamily: 'var(--font-annot)', fontSize: 10, fill: 'var(--ink-faint)' }}
          />
          <YAxis hide />
          <Tooltip
            formatter={(v: number, name: string) => [
              `${v.toFixed(0)} km`,
              name === 'planned_km' ? '计划' : '实际',
            ]}
            contentStyle={{ fontFamily: 'var(--font-hand)', fontSize: 11, border: '1px solid var(--rule)' }}
          />
          <Bar dataKey="planned_km" fill="var(--rule)" radius={[2, 2, 0, 0]} />
          <Bar dataKey="executed_km" fill="var(--ink)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
