import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Copy, Pencil, Plus, RefreshCw, Send, Square, Trash2 } from "lucide-react";
import { api, fmtTime, streamChat } from "../api";
import { Empty, useToast } from "../ui";

type Msg = { role: string; content: string; created_at?: string };
const SUGGESTIONS = ["Explain how a neural network learns", "Give me a study plan for machine learning", "Write a SQL query to find duplicate emails"];

export default function Chat() {
  const toast = useToast();
  const [convs, setConvs] = useState<any[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [providers, setProviders] = useState<any[]>([]);
  const [provider, setProvider] = useState("");
  const abort = useRef<AbortController | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  const refresh = () => api("/api/conversations").then(setConvs).catch(() => {});
  const open = async (id: string) => {
    try { const c = await api(`/api/conversations/${id}`); setActive(id); setMsgs(c.messages); setError(""); }
    catch (e: any) { toast(e.message, "err"); }
  };

  useEffect(() => {
    refresh();
    api("/api/models").then((m) => { setProviders(m.providers); setProvider(m.default_provider); }).catch((e) => setError(e.message));
    const id = sessionStorage.getItem("nexora:conv");
    if (id) { sessionStorage.removeItem("nexora:conv"); open(id); }
    const p = sessionStorage.getItem("nexora:prompt");
    if (p) { sessionStorage.removeItem("nexora:prompt"); setInput(p); }
  }, []);
  useEffect(() => { if (stick.current && box.current) box.current.scrollTop = box.current.scrollHeight; }, [msgs]);

  const send = async (regenerate = false, text?: string) => {
    const t = (text ?? input).trim();
    if (!regenerate && !t) return;
    setError(""); setBusy(true); stick.current = true;
    const base = regenerate && msgs.at(-1)?.role === "assistant" ? msgs.slice(0, -1) : msgs;
    setMsgs(regenerate ? [...base, { role: "assistant", content: "" }]
      : [...base, { role: "user", content: t, created_at: new Date().toISOString() }, { role: "assistant", content: "" }]);
    if (!regenerate) setInput("");
    const ac = new AbortController(); abort.current = ac;
    let acc = "";
    try {
      await streamChat({ conversation_id: active, message: regenerate ? undefined : t, regenerate, provider }, ac.signal,
        (c) => { acc += c; setMsgs((m) => { const n = [...m]; n[n.length - 1] = { ...n[n.length - 1], content: acc }; return n; }); },
        (id) => setActive(id));
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setError(e.message);
        setMsgs((m) => (m.at(-1)?.role === "assistant" && !m.at(-1)?.content ? m.slice(0, -1) : m));
      }
    } finally { setBusy(false); refresh(); }
  };

  const rename = async (c: any) => {
    const title = window.prompt("Rename conversation", c.title);
    if (title?.trim()) { await api(`/api/conversations/${c.id}`, { method: "PATCH", json: { title } }).catch((e) => toast(e.message, "err")); refresh(); }
  };
  const remove = async (c: any) => {
    if (!window.confirm(`Delete "${c.title}"?`)) return;
    await api(`/api/conversations/${c.id}`, { method: "DELETE" }).catch((e) => toast(e.message, "err"));
    if (active === c.id) { setActive(null); setMsgs([]); }
    refresh();
  };
  const cur = providers.find((p) => p.id === provider);

  return (
    <div className="chat">
      <aside className="convs" aria-label="Conversations">
        <button className="btn" onClick={() => { setActive(null); setMsgs([]); setError(""); }}><Plus size={16} /> New chat</button>
        {convs.map((c) => (
          <div key={c.id} className={`conv ${c.id === active ? "on" : ""}`} onClick={() => open(c.id)}>
            <span>{c.title}</span>
            <button className="btn ghost sm" aria-label="Rename" onClick={(e) => { e.stopPropagation(); rename(c); }}><Pencil size={13} /></button>
            <button className="btn ghost sm" aria-label="Delete" onClick={(e) => { e.stopPropagation(); remove(c); }}><Trash2 size={13} /></button>
          </div>
        ))}
      </aside>
      <section className="chatmain">
        <div className="row spread" style={{ marginBottom: 8 }}>
          <label style={{ flexDirection: "row", alignItems: "center" }}>Provider
            <select value={provider} onChange={(e) => setProvider(e.target.value)} style={{ width: "auto" }}>
              {providers.map((p) => <option key={p.id} value={p.id}>{p.label}{p.ready ? "" : " (not configured)"}</option>)}
            </select></label>
          {cur && <span className={`badge ${cur.ready ? "ok" : "bad"}`}>{cur.ready ? "Ready" : "Not configured"}{cur.kind === "demo" ? " · demo, not an LLM" : ""}</span>}
        </div>
        <div className="msgs" ref={box} onScroll={(e) => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120; }}>
          {!msgs.length && <Empty title="Start a conversation" hint="Pick a suggestion or type below.">
            <div className="chips" style={{ justifyContent: "center", marginTop: 8 }}>{SUGGESTIONS.map((s) => <button key={s} className="btn ghost sm" onClick={() => send(false, s)}>{s}</button>)}</div>
          </Empty>}
          {msgs.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.role === "assistant" ? (m.content ? <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{m.content}</ReactMarkdown> : <span className="muted">Thinking…</span>) : m.content}
              <div className="row small" style={{ marginTop: 6, opacity: 0.75 }}>
                {m.created_at && <span>{fmtTime(m.created_at)}</span>}
                {m.role === "assistant" && m.content && <button className="btn ghost sm" onClick={() => { navigator.clipboard.writeText(m.content); toast("Copied"); }}><Copy size={12} /> Copy</button>}
                {m.role === "assistant" && i === msgs.length - 1 && !busy && <button className="btn ghost sm" onClick={() => send(true)}><RefreshCw size={12} /> Regenerate</button>}
              </div>
            </div>
          ))}
        </div>
        {error && <div className="err row spread" role="alert"><span>{error}</span>{msgs.length > 0 && msgs.at(-1)?.role === "user" && <button className="btn ghost sm" onClick={() => send(true)}>Retry</button>}</div>}
        <div className="composer">
          <textarea aria-label="Message" value={input} placeholder="Message Nexora… (Enter to send, Shift+Enter for a new line)" rows={1}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (!busy) send(); } }} />
          {busy ? <button className="btn" onClick={() => abort.current?.abort()}><Square size={14} /> Stop</button>
            : <button className="btn" onClick={() => send()} disabled={!input.trim()}><Send size={14} /> Send</button>}
        </div>
      </section>
    </div>
  );
}
