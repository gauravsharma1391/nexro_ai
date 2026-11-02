import { useEffect, useState } from "react";
import { Download, Upload } from "lucide-react";
import { api, upload } from "../api";
import { Empty, Spinner, useToast } from "../ui";
import ChartView from "../components/ChartView";
import DataTable from "../components/DataTable";
import CleanPanel from "../components/CleanPanel";

const TABS = ["Overview", "Data", "Charts", "Clean", "Ask"];
const CHARTS = ["bar", "line", "histogram", "scatter", "pie", "box", "heatmap"];

function Charts({ id, cols }: { id: string; cols: any[] }) {
  const [t, setT] = useState("bar");
  const [x, setX] = useState("");
  const [y, setY] = useState("");
  const [agg, setAgg] = useState("sum");
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");
  const names = cols.map((c) => c.name), nums = cols.filter((c) => c.type === "numeric").map((c) => c.name);
  const run = async () => {
    setErr(""); setRes(null);
    try { setRes(await api(`/api/analytics/${id}/chart`, { method: "POST", json: { type: t, x: x || null, y: y || null, agg } })); } catch (e: any) { setErr(e.message); }
  };
  return (
    <div className="stack">
      <div className="row">
        <label>Chart<select value={t} onChange={(e) => setT(e.target.value)}>{CHARTS.map((c) => <option key={c}>{c}</option>)}</select></label>
        {t !== "heatmap" && <label>{t === "box" ? "Group by (optional)" : "X / category"}<select value={x} onChange={(e) => setX(e.target.value)}><option value="">—</option>{(["scatter", "histogram"].includes(t) ? nums : names).map((c) => <option key={c}>{c}</option>)}</select></label>}
        {["bar", "line", "scatter", "box"].includes(t) && <label>Y (numeric){t === "bar" ? ", optional" : ""}<select value={y} onChange={(e) => setY(e.target.value)}><option value="">—</option>{nums.map((c) => <option key={c}>{c}</option>)}</select></label>}
        {["bar", "line"].includes(t) && <label>Aggregate<select value={agg} onChange={(e) => setAgg(e.target.value)}>{["sum", "mean", "median", "min", "max", "count"].map((a) => <option key={a}>{a}</option>)}</select></label>}
        <button className="btn" onClick={run}>Draw chart</button>
      </div>
      {err && <div className="err" role="alert">{err}</div>}
      {res ? <ChartView type={res.type} data={res.data} /> : <Empty title="Pick columns and draw a chart" />}
      {res?.type === "heatmap" && <div className="note">Correlation does not imply causation.</div>}
    </div>
  );
}

function Ask({ id }: { id: string }) {
  const [q, setQ] = useState("");
  const [r, setR] = useState<any>(null);
  const [err, setErr] = useState("");
  const go = async () => { setErr(""); try { setR(await api(`/api/analytics/${id}/ask`, { method: "POST", json: { question: q } })); } catch (e: any) { setErr(e.message); } };
  return (
    <div className="stack">
      <div className="note">Questions are matched to a fixed set of safe pandas operations. No generated code is run and no AI model sees your data.</div>
      <div className="row"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Which columns contain missing values?" onKeyDown={(e) => e.key === "Enter" && q.trim() && go()} style={{ flex: 1 }} /><button className="btn" onClick={go} disabled={!q.trim()}>Ask</button></div>
      <div className="chips">{["Summarize this dataset", "Which columns contain missing values?", "Find the strongest correlations", "Explain the unusual values"].map((s) => <button key={s} className="btn ghost sm" onClick={() => setQ(s)}>{s}</button>)}</div>
      {err && <div className="err">{err}</div>}
      {r && <div className="card stack"><p style={{ margin: 0 }}>{r.answer}</p>
        {r.table && <div className="tablewrap"><table><thead><tr>{Object.keys(r.table[0]).map((c) => <th key={c}>{c}</th>)}</tr></thead><tbody>{r.table.map((row: any, i: number) => <tr key={i}>{Object.values(row).map((v: any, j) => <td key={j}>{String(v)}</td>)}</tr>)}</tbody></table></div>}
        {r.chart && <ChartView type={r.chart.type} data={r.chart.data} />}
        <span className="muted small">Source: {r.source}</span></div>}
    </div>
  );
}

export default function Analytics() {
  const toast = useToast();
  const [ds, setDs] = useState<{ id: string; name: string } | null>(null);
  const [sum, setSum] = useState<any>(null);
  const [list, setList] = useState<any[]>([]);
  const [tab, setTab] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const refreshList = () => api("/api/analytics/datasets").then(setList).catch(() => {});
  useEffect(() => { refreshList(); }, []);
  const select = async (id: string, name: string) => {
    setBusy(true); setErr(""); setSum(null); setDs({ id, name }); setTab(0);
    try { setSum(await api(`/api/analytics/${id}/summary`, { method: "POST" })); } catch (e: any) { setErr(e.message); setDs(null); } finally { setBusy(false); }
  };
  const onFile = async (f?: File) => {
    if (!f) return;
    setBusy(true); setErr("");
    try { const r = await upload("/api/analytics/upload", f); refreshList(); await select(r.dataset_id, r.filename); } catch (e: any) { setErr(e.message); setBusy(false); }
  };
  const cols = sum?.columns || [];

  return (
    <div className="stack">
      <div><h1>Analytics Studio</h1><p className="sub">Upload a .csv or .xlsx file. It stays on your machine and your original is never modified.</p></div>
      <div className="card row">
        <label><span className="row"><Upload size={14} /> Upload a dataset</span><input type="file" accept=".csv,.xlsx" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} /></label>
        {list.length > 0 && <label>Or reopen<select value={ds?.id || ""} onChange={(e) => { const d = list.find((x) => x.id === e.target.value); if (d) select(d.id, d.filename); }}><option value="">Recent datasets…</option>{list.map((d) => <option key={d.id} value={d.id}>{d.filename} ({d.rows} rows)</option>)}</select></label>}
        {busy && <Spinner />}
      </div>
      {err && <div className="err" role="alert">{err}</div>}
      {!ds && !busy && <Empty title="No dataset open" hint="Upload a file to see statistics, charts and cleaning tools." />}
      {ds && sum && <>
        <div className="row spread"><b>{ds.name}</b><span className="row">
          <a className="btn ghost sm" href={`/api/analytics/${ds.id}/export.csv`} download><Download size={12} /> CSV</a>
          <a className="btn ghost sm" href={`/api/analytics/${ds.id}/export.json`} download={`${ds.name}-summary.json`}><Download size={12} /> JSON summary</a></span></div>
        <div className="grid g4">{([["Rows", sum.overview.rows], ["Columns", sum.overview.cols], ["Missing cells", sum.overview.missing_cells], ["Duplicate rows", sum.overview.duplicate_rows]] as const).map(([l, v]) => <div className="card stat" key={l}><b>{v}</b><span className="muted small">{l}</span></div>)}</div>
        <div className="tabs" role="tablist">{TABS.map((t, i) => <button key={t} role="tab" aria-selected={tab === i} className={`tab ${tab === i ? "on" : ""}`} onClick={() => setTab(i)}>{t}</button>)}</div>
        {tab === 0 && <div className="stack">
          <div className="tablewrap"><table><thead><tr>{["Column", "Type", "Missing", "Unique", "Mean", "Median", "Mode", "Std", "Min", "Max", "Outliers (IQR)"].map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>{cols.map((c: any) => <tr key={c.name}><td>{c.name}</td><td>{c.type}</td><td>{c.missing} ({c.missing_pct}%)</td><td>{c.unique}</td>
              {c.type === "numeric" ? <><td>{c.mean}</td><td>{c.median}</td><td>{c.mode}</td><td>{c.std}</td><td>{c.min}</td><td>{c.max}</td><td>{c.outliers.count}</td></>
                : <td colSpan={7} className="muted">{c.top_values.map((v: any) => `${v.value} (${v.count})`).join(", ")}</td>}</tr>)}</tbody></table></div>
          <div className="note">Outliers use the IQR rule: values more than 1.5 × IQR beyond the quartiles. Unusual values are not necessarily errors.</div>
          <h2>Correlations</h2><ChartView type="heatmap" data={sum.correlations} />
          {sum.correlations.top_pairs.length > 0 && <div className="chips">{sum.correlations.top_pairs.map((p: any) => <span className="chip" key={p.a + p.b}>{p.a} ↔ {p.b}: {p.r}</span>)}</div>}
          <div className="note">Correlation does not imply causation.</div></div>}
        {tab === 1 && <DataTable id={ds.id} columns={cols} />}
        {tab === 2 && <Charts id={ds.id} cols={cols} />}
        {tab === 3 && <CleanPanel id={ds.id} columns={cols} onApplied={(nid) => { refreshList(); select(nid, "cleaned_" + ds.name); toast("Now viewing the cleaned copy."); }} />}
        {tab === 4 && <Ask id={ds.id} />}
      </>}
    </div>
  );
}
