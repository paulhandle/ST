'use client'

import type { DashboardGoal } from '@/lib/api/types'
import { formatTime } from '@/lib/api/types'
import { LineChart, Line, ResponsiveContainer, Tooltip, YAxis } from 'recharts'

interface Props {
  goal: DashboardGoal
}

export default function GoalCard({ goal }: Props) {
  const trend = goal.monthly_delta_sec
  const trendStr = trend === 0 ? '持平' :
    trend < 0 ? `快了 ${formatTime(Math.abs(trend))}` :
    `慢了 ${formatTime(trend)}`
  const trendColor = trend < 0 ? 'var(--ink)' : trend > 0 ? 'var(--accent)' : 'var(--ink-faint)'

  const chartData = goal.prediction_history.map((p, i) => ({
    i,
    t: p.predicted_time_sec,
  }))

  return (
    <div style={{ margin: '12px 16px' }} className="sk-card">
      <div className="between" style={{ marginBottom: 8 }}>
        <span className="hand" style={{ fontSize: 13, fontWeight: 700 }}>目标</span>
        <span className="hand text-faint" style={{ fontSize: 12 }}>{goal.days_until} 天后</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12 }}>
        <div>
          <div className="hand" style={{ fontSize: 28, fontWeight: 700, lineHeight: 1 }}>
            {goal.label}
          </div>
          <div className="hand" style={{ fontSize: 12, color: trendColor, marginTop: 4 }}>
            ↑ {trendStr}（过去30天）
          </div>
        </div>

        {chartData.length > 1 && (
          <div style={{ flex: 1, height: 40 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <YAxis domain={['dataMin - 60', 'dataMax + 60']} hide />
                <Line
                  type="monotone"
                  dataKey="t"
                  stroke="var(--ink)"
                  strokeWidth={1.5}
                  dot={false}
                />
                <Tooltip
                  formatter={(v: number) => [formatTime(v), '预测完赛']}
                  contentStyle={{ fontFamily: 'var(--font-hand)', fontSize: 12, border: '1px solid var(--rule)' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="hand text-faint" style={{ fontSize: 11, marginTop: 8 }}>
        {goal.race_date} 比赛日
      </div>
    </div>
  )
}
