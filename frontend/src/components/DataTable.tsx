import { useEffect, useState } from "react";
import { api } from "../api";
import { Empty, Spinner } from "../ui";

export default function DataTable({ id, columns }: { id: string; columns: any[] }) {
  const [q, setQ] = useState({ page: 1, search: "", sort: "", desc: false, filter_col: "", min: "", max: "" });
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState("");
  const numeric = columns.filter((c) => c.type === "numeric");

  useEffect(() => {
    const sp = new URLSearchParams({ page: String(q.page), page_size: "25" });
    (["search", "sort", "filter_col", "min", "max"] as const).forEach((k) => q[k] !== "" && sp.set(k, q[k]));
    if (q.desc) sp.set("desc", "true");
    setErr("");
    const t = setTimeout(() => api(`/api/analytics/${id}/preview?${sp}`).then(setData).catch((e) => setErr(e.message)), 250);
    return () => clearTimeout(t);
  }, [id, q]);

  const set = (patch: object) => setQ({ ...q, page: 1, ...patch });
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  return (
    <div className="stack">
      <div className="row">
        <input aria-label="Search" placeholder="Search all columns" value={q.search} onChange={(e) => set({ search: e.target.value })} style={{ maxWidth: 240 }} />
        <select aria-label="Sort column" value={q.sort} onChange={(e) => set({ sort: e.target.value })} style={{ width: "auto" }}><option value="">Sort by…</option>{columns.map((c) => <option key={c.name}>{c.name}</option>)}</select>
        <label style={{ flexDirection: "row", alignItems: "center" }}><input type="checkbox" checked={q.desc} onChange={(e) => set({ desc: e.target.checked })} /> descending</label>
        <select aria-label="Filter column" value={q.filter_col} onChange={(e) => set({ filter_col: e.target.value })} style={{ width: "auto" }}><option value="">Numeric filter…</option>{numeric.map((c) => <option key={c.name}>{c.name}</option>)}</select>
        {q.filter_col && <><input aria-label="Minimum" type="number" placeholder="min" value={q.min} onChange={(e) => set({ min: e.target.value })} style={{ width: 90 }} /><input aria-label="Maximum" type="number" placeholder="max" value={q.max} onChange={(e) => set({ max: e.target.value })} style={{ width: 90 }} /></>}
      </div>
      {err && <div className="err">{err}</div>}
      {!data && !err && <Spinner />}
      {data && (data.rows.length ? <div className="tablewrap"><table><thead><tr>{data.columns.map((c: string) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{data.rows.map((r: any, i: number) => <tr key={i}>{data.columns.map((c: string) => <td key={c}>{r[c] == null ? <span className="muted">null</span> : String(r[c])}</td>)}</tr>)}</tbody></table></div>
        : <Empty title="No matching rows" hint="Clear the search or filter." />)}
      {data && <div className="row spread"><span className="muted small">{data.total} rows · page {data.page} of {pages}</span>
        <span className="row"><button className="btn ghost sm" disabled={q.page <= 1} onClick={() => setQ({ ...q, page: q.page - 1 })}>Previous</button><button className="btn ghost sm" disabled={q.page >= pages} onClick={() => setQ({ ...q, page: q.page + 1 })}>Next</button></span></div>}
    </div>
  );
}
