import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const GREEN = '#244B45'
const GOLD = '#D9A441'
const axis = { fontSize: 11, fill: '#6F756F' }

export const shortDate = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString([], { month: 'short', day: 'numeric' })

export function ChartCard({ title, subtitle, children, empty }) {
  return (
    <section className="card-index rounded-lg p-4">
      <h3 className="font-display font-semibold text-[15px]">{title}</h3>
      {subtitle && <p className="text-[12px] text-muted mb-3">{subtitle}</p>}
      {empty ? <div className="h-[200px] flex items-center justify-center text-sm text-muted">No data in this period yet.</div>
        : <div role="img" aria-label={title} className="h-[220px] mt-2">{children}</div>}
    </section>
  )
}

export function DayLine({ data, color = GREEN }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid stroke="#E3E0D8" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} minTickGap={24} />
        <YAxis allowDecimals={false} tick={axis} />
        <Tooltip labelFormatter={shortDate} />
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function DayBars({ data, color = GOLD }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid stroke="#E3E0D8" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} minTickGap={24} />
        <YAxis allowDecimals={false} tick={axis} />
        <Tooltip labelFormatter={shortDate} />
        <Bar dataKey="value" fill={color} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

/** Horizontal bars for ranked categories. */
export function RankBars({ data, dataKey = 'count', nameKey = 'label', color = GREEN, max }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#E3E0D8" horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={axis} domain={max ? [0, max] : undefined} />
        <YAxis type="category" dataKey={nameKey} width={110} tick={axis} />
        <Tooltip />
        <Bar dataKey={dataKey} fill={color} radius={[0, 3, 3, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
