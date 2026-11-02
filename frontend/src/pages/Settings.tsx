import { useEffect, useState } from "react";
import { api } from "../api";

export default function Settings({ theme, toggle }: { theme: string; toggle: () => void }) {
  const [m, setM] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api("/api/models").then(setM).catch((e) => setErr(e.message)); }, []);
  return (
    <div className="stack">
      <div><h1>Settings</h1><p className="sub">Secrets live in the backend .env file; they are never sent to this page.</p></div>
      {err && <div className="err">{err}</div>}
      <div className="card"><h2>Appearance</h2><button className="btn ghost" onClick={toggle}>Current theme: {theme}. Switch</button></div>
      {m && <>
        <div className="card"><h2>AI providers</h2>
          {m.providers.map((p: any) => (
            <p key={p.id} className="row spread"><span><b>{p.label}</b> <span className="muted small">model: {p.model}</span>{!p.ready && <span className="muted small"> · {p.hint}</span>}</span>
              <span className={`badge ${p.ready ? "ok" : "bad"}`}>{p.ready ? "Ready" : "Not configured"}</span></p>))}
          <p className="muted small">Default provider: {m.default_provider}</p></div>
        <div className="card"><h2>Limits (set in .env)</h2><div className="chips">{Object.entries(m.limits).map(([k, v]) => <span className="chip" key={k}>{k}: {String(v)}</span>)}</div></div>
        <div className="card"><h2>Optional packages installed</h2><div className="chips">{Object.entries(m.optional_dependencies).map(([k, v]) => <span key={k} className={`badge ${v ? "ok" : "bad"}`}>{k}: {v ? "yes" : "no"}</span>)}</div></div>
      </>}
      <p className="muted small">This is a single-user, local application: there is no login. Do not expose it to the internet without adding authentication.</p>
    </div>
  );
}
