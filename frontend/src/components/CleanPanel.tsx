import { useState } from "react";
import { api } from "../api";
import { useToast } from "../ui";

export default function CleanPanel({ id, columns, onApplied }: { id: string; columns: any[]; onApplied: (newId: string) => void }) {
  const toast = useToast();
  const [dedupe, setDedupe] = useState(false);
  const [fillCol, setFillCol] = useState("");
  const [strategy, setStrategy] = useState("drop");
  const [value, setValue] = useState("");
  const [fCol, setFCol] = useState("");
  const [fMin, setFMin] = useState("");
  const [fMax, setFMax] = useState("");
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");
  const numeric = columns.filter((c) => c.type === "numeric");

  const ops = () => {
    const o: any[] = [];
    if (dedupe) o.push({ op: "drop_duplicates" });
    if (fillCol) o.push({ op: "fill_missing", column: fillCol, strategy, value });
    if (fCol) o.push({ op: "filter_numeric", column: fCol, min: fMin === "" ? null : Number(fMin), max: fMax === "" ? null : Number(fMax) });
    return o;
  };
  const run = async (apply: boolean) => {
    const o = ops();
    if (!o.length) { setErr("Choose at least one cleaning step."); return; }
    setErr("");
    try {
      const r = await api(`/api/analytics/${id}/clean`, { method: "POST", json: { ops: o, apply } });
      setRes(r);
      if (apply) { toast("Saved as a new dataset. Your original is unchanged."); onApplied(r.new_dataset_id); }
    } catch (e: any) { setErr(e.message); }
  };
  return (
    <div className="stack">
      <div className="note">Cleaning never changes your original data. Preview first; applying saves a new dataset.</div>
      <label style={{ flexDirection: "row", alignItems: "center" }}><input type="checkbox" checked={dedupe} onChange={(e) => setDedupe(e.target.checked)} /> Remove duplicate rows</label>
      <div className="row"><b className="small">Missing values:</b>
        <select aria-label="Column" value={fillCol} onChange={(e) => setFillCol(e.target.value)} style={{ width: "auto" }}><option value="">(skip)</option>{columns.filter((c) => c.missing > 0).map((c) => <option key={c.name}>{c.name}</option>)}</select>
        <select aria-label="Strategy" value={strategy} onChange={(e) => setStrategy(e.target.value)} style={{ width: "auto" }}><option value="drop">drop rows</option><option value="mean">fill with mean</option><option value="median">fill with median</option><option value="mode">fill with most common</option><option value="value">fill with value</option></select>
        {strategy === "value" && <input aria-label="Value" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 120 }} />}</div>
      <div className="row"><b className="small">Numeric filter:</b>
        <select aria-label="Filter column" value={fCol} onChange={(e) => setFCol(e.target.value)} style={{ width: "auto" }}><option value="">(skip)</option>{numeric.map((c) => <option key={c.name}>{c.name}</option>)}</select>
        <input aria-label="Min" type="number" placeholder="min" value={fMin} onChange={(e) => setFMin(e.target.value)} style={{ width: 90 }} /><input aria-label="Max" type="number" placeholder="max" value={fMax} onChange={(e) => setFMax(e.target.value)} style={{ width: 90 }} /></div>
      <div className="row"><button className="btn ghost" onClick={() => run(false)}>Preview changes</button><button className="btn" onClick={() => run(true)} disabled={!res}>Apply as new dataset</button></div>
      {err && <div className="err" role="alert">{err}</div>}
      {res && <div className="card"><p>Rows {res.before.rows} → <b>{res.after.rows}</b> · missing cells {res.before.missing_cells} → <b>{res.after.missing_cells}</b> · duplicates {res.before.duplicate_rows} → <b>{res.after.duplicate_rows}</b></p>
        <div className="tablewrap"><table><thead><tr>{Object.keys(res.preview[0] || {}).map((c) => <th key={c}>{c}</th>)}</tr></thead><tbody>{res.preview.map((r: any, i: number) => <tr key={i}>{Object.values(r).map((v: any, j) => <td key={j}>{v == null ? "null" : String(v)}</td>)}</tr>)}</tbody></table></div></div>}
    </div>
  );
}
