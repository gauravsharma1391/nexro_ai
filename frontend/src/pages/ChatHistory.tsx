import { useEffect, useState } from "react";
import { api, fmtTime } from "../api";
import { Empty, useToast } from "../ui";

export default function ChatHistory({ go }: { go: (id: string) => void }) {
  const toast = useToast();
  const [items, setItems] = useState<any[] | null>(null);
  const [q, setQ] = useState("");
  const load = () => api("/api/conversations").then(setItems).catch((e) => { toast(e.message, "err"); setItems([]); });
  useEffect(() => { load(); }, []);
  const shown = (items || []).filter((c) => c.title.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="stack">
      <div><h1>Chat history</h1><p className="sub">Conversations are stored locally in SQLite.</p></div>
      <input aria-label="Search conversations" placeholder="Search by title" value={q} onChange={(e) => setQ(e.target.value)} />
      {items && !shown.length && <Empty title="No conversations found" hint="Start one in AI Chat." />}
      {shown.map((c) => (
        <div key={c.id} className="card row spread">
          <div><b>{c.title}</b><div className="muted small">{c.message_count} messages · updated {fmtTime(c.updated_at)}</div></div>
          <div className="row">
            <button className="btn sm" onClick={() => { sessionStorage.setItem("nexora:conv", c.id); go("chat"); }}>Open</button>
            <button className="btn danger sm" onClick={async () => { if (window.confirm("Delete this conversation?")) { await api(`/api/conversations/${c.id}`, { method: "DELETE" }); load(); } }}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}
