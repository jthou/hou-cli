/**
 * 预报温度趋势图（Recharts：最高/最低温度曲线）
 */
import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function formatLabel(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr + 'T12:00:00')
  if (isNaN(d)) return dateStr.slice(5) || '-'
  const today = new Date()
  const isToday = d.toDateString() === today.toDateString()
  return isToday ? '今天' : WEEKDAYS[d.getDay()]
}

function toNum(v) {
  if (v == null || v === '') return NaN
  const n = Number(v)
  return Number.isFinite(n) ? n : NaN
}

export default function TemperatureTrendChart({ daily }) {
  const data = useMemo(() => {
    if (!Array.isArray(daily) || daily.length === 0) return []
    return daily.map((d) => {
      const tMax = toNum(d.temp_max ?? d.tempMax)
      const tMin = toNum(d.temp_min ?? d.tempMin)
      const dateStr = d.date ?? d.fxDate
      return {
        name: formatLabel(dateStr),
        dateStr,
        tempMax: isNaN(tMax) ? null : tMax,
        tempMin: isNaN(tMin) ? null : tMin,
      }
    })
  }, [daily])

  if (!data.length || data.length < 2) return null

  const CustomDot = ({ cx, cy, payload, type }) => {
    const val = type === 'max' ? payload?.tempMax : payload?.tempMin
    if (val == null) return null
    const isOnly = payload?.tempMax === payload?.tempMin
    if (type === 'min' && isOnly) return null
    const color = type === 'max' ? 'rgb(251 191 36)' : 'rgb(34 211 238)'
    return (
      <g>
        <text x={cx} y={type === 'max' ? cy - 6 : cy + 14} textAnchor="middle" fill={color} fontSize={12} fontWeight={500}>
          {val}°
        </text>
      </g>
    )
  }

  const CustomizedXAxisTick = ({ x, y, payload }) => {
    const highlight = payload?.value === '今天'
    return (
      <g transform={`translate(${x},${y})`}>
        <text x={0} y={0} dy={12} textAnchor="middle" fill={highlight ? '#007acc' : '#64748b'} fontSize={12} fontWeight={highlight ? 500 : 400}>
          {payload?.value ?? ''}
        </text>
      </g>
    )
  }

  return (
    <div className="mt-3">
      <div className="flex items-center gap-4 mb-1.5 text-xs">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded bg-amber-400" />
          <span className="text-amber-400/90">最高</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded bg-cyan-400" />
          <span className="text-cyan-400/90">最低</span>
        </span>
      </div>
      <div className="h-[120px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 20, right: 12, left: 12, bottom: 8 }}>
            <CartesianGrid strokeDasharray="2 2" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="name" tick={<CustomizedXAxisTick />} axisLine={false} tickLine={false} />
            <YAxis domain={['auto', 'auto']} hide />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(37,37,38,0.95)', border: '1px solid #3e3e42', borderRadius: 8 }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(val, name) => [
                `${val}°`,
                name === 'tempMax' ? '最高' : '最低',
              ]}
            />
            <Line
              type="monotone"
              dataKey="tempMax"
              stroke="rgb(251 191 36)"
              strokeWidth={1}
              dot={(props) => <CustomDot {...props} type="max" />}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="tempMin"
              stroke="rgb(34 211 238)"
              strokeWidth={1}
              dot={(props) => <CustomDot {...props} type="min" />}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
