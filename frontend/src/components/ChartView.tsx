import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

const COLORS = ["#5cc8f2", "#b79cff", "#5fd6a0", "#ffb86b", "#ff7a8a", "#7aa2ff", "#e6a8ff", "#9be15d", "#8d97b3"];
const axis = { stroke: "var(--muted)", fontSize: 12 };

function Box({ data }: { data: any[] }) {
  const all = data.flatMap((d) => [d.min, d.max]);
  const lo = Math.min(...all), hi = Math.max(...all), span = hi - lo || 1;
  const X = (v: number) => 90 + ((v - lo) / span) * 560;
  return (
    <svg viewBox={`0 0 680 ${data.length * 46 + 10}`} width="100%" role="img" aria-label="Box plot">
      {data.map((d, i) => { const y = i * 46 + 26; return (
        <g key={d.name}>
          <text x="4" y={y + 4} fill="var(--muted)" fontSize="12">{String(d.name).slice(0, 12)}</text>
          <line x1={X(d.min)} x2={X(d.max)} y1={y} y2={y} stroke="var(--muted)" />
          <rect x={X(d.q1)} y={y - 12} width={Math.max(2, X(d.q3) - X(d.q1))} height="24" fill="var(--accent)" opacity="0.35" stroke="var(--accent)" />
          <line x1={X(d.median)} x2={X(d.median)} y1={y - 12} y2={y + 12} stroke="var(--text)" strokeWidth="2" />
          <title>{`min ${d.min}, Q1 ${d.q1}, median ${d.median}, Q3 ${d.q3}, max ${d.max}, outliers ${d.outliers}`}</title>
        </g>); })}
      <text x="90" y={data.length * 46 + 6} fill="var(--muted)" fontSize="11">{lo} … {hi} (whiskers: 1.5 × IQR; hover for values)</text>
    </svg>
  );
}

function Heat({ data }: { data: { columns: string[]; matrix: (number | null)[][] } }) {
  if (!data.columns.length) return <p className="muted">Needs at least two numeric columns.</p>;
  return (
    <div className="tablewrap"><table><thead><tr><th />{data.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>{data.matrix.map((r, i) => <tr key={i}><th>{data.columns[i]}</th>{r.map((v, j) => (
        <td key={j} title={String(v)} style={{ background: v == null ? undefined : `color-mix(in srgb,${v >= 0 ? "var(--accent)" : "var(--danger)"} ${Math.abs(v) * 70}%,transparent)` }}>{v == null ? "–" : v.toFixed(2)}</td>))}</tr>)}</tbody></table></div>
  );
}

export default function ChartView({ type, data }: { type: string; data: any }) {
  if (type === "heatmap") return <Heat data={data} />;
  if (type === "box") return data.length ? <Box data={data} /> : <p className="muted">No numeric values to plot.</p>;
  if (!data.length) return <p className="muted">No data to plot.</p>;
  const h = 320;
  return (
    <div style={{ height: h }}><ResponsiveContainer>
      {type === "pie" ? (
        <PieChart><Pie data={data} dataKey="value" nameKey="name" outerRadius={120} label>{data.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart>
      ) : type === "line" ? (
        <LineChart data={data}><CartesianGrid stroke="var(--line)" /><XAxis dataKey="x" {...axis} /><YAxis {...axis} /><Tooltip /><Line dataKey="y" stroke="#5cc8f2" dot={data.length < 40} /></LineChart>
      ) : type === "scatter" ? (
        <ScatterChart><CartesianGrid stroke="var(--line)" /><XAxis dataKey="x" type="number" name="x" {...axis} /><YAxis dataKey="y" type="number" name="y" {...axis} /><Tooltip cursor={{ strokeDasharray: "3 3" }} /><Scatter data={data} fill="#5cc8f2" /></ScatterChart>
      ) : (
        <BarChart data={data}><CartesianGrid stroke="var(--line)" /><XAxis dataKey={type === "histogram" ? "bin" : "x"} {...axis} /><YAxis {...axis} /><Tooltip /><Bar dataKey={type === "histogram" ? "count" : "y"} fill="#5cc8f2" /></BarChart>
      )}
    </ResponsiveContainer></div>
  );
}
