import { useEffect, useState } from "react";
import { BarChart3, BrainCircuit, MessageSquare, Type } from "lucide-react";
import { api, fmtTime } from "../api";
import { Empty, Spinner } from "../ui";

const EXAMPLES = ["Explain overfitting in simple terms", "Write a Python function that removes duplicates from a list", "What is the difference between TF-IDF and Bag of Words?"];

export default function Dashboard({ go }: { go: (id: string) => void }) {
  const [stats, setStats] = useState<any>(null);
  const [convs, setConvs] = useState<any[]>([]);
  const [sets, setSets] = useState<any[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api("/api/stats"), api("/api/conversations"), api("/api/analytics/datasets")])
      .then(([s, c, d]) => { setStats(s); setConvs(c.slice(0, 5)); setSets(d.slice(0, 5)); })
      .catch((e) => setErr(e.message));
  }, []);

  const ask = (p: string) => { sessionStorage.setItem("nexora:prompt", p); go("chat"); };
  const tiles = [
    { id: "chat", icon: MessageSquare, t: "AI Chat", d: "Talk to a configured LLM or the labeled demo helper." },
    { id: "nlp", icon: Type, t: "NLP Lab", d: "Preprocess, summarize, extract keywords, analyze sentiment." },
    { id: "dl", icon: BrainCircuit, t: "Deep Learning Lab", d: "Train a small neural network and inspect real curves." },
    { id: "analytics", icon: BarChart3, t: "Analytics Studio", d: "Upload CSV/XLSX, explore, chart, clean and export." },
  ];
  return (
    <div className="stack">
      <div><h1>Welcome to Nexora AI</h1><p className="sub">Chat, language tools, neural networks and data analysis in one place.</p></div>
      {err && <div className="err">{err}</div>}
      <div className="grid g4">{tiles.map((t) => (
        <button key={t.id} className="card tile" onClick={() => go(t.id)}><t.icon size={22} color="var(--accent)" /><h3>{t.t}</h3><span className="muted small">{t.d}</span></button>
      ))}</div>
      <div className="grid g4">
        {stats ? ([["Conversations", stats.conversations], ["Messages sent", stats.user_messages], ["Datasets analyzed", stats.datasets]] as const).map(([l, v]) => (
          <div className="card stat" key={l}><b>{v}</b><span className="muted small">{l} (from stored data)</span></div>
        )) : !err && <Spinner />}
      </div>
      <div className="grid g2">
        <div className="card"><h2>Recent conversations</h2>
          {convs.length ? convs.map((c) => <p key={c.id} className="row spread"><span>{c.title}</span><span className="muted small">{fmtTime(c.updated_at)}</span></p>)
            : <Empty title="No conversations yet" hint="Start one from AI Chat." />}</div>
        <div className="card"><h2>Recent analytics sessions</h2>
          {sets.length ? sets.map((d) => <p key={d.id} className="row spread"><span>{d.filename}</span><span className="muted small">{d.rows} rows</span></p>)
            : <Empty title="No datasets yet" hint="Upload a CSV in Analytics Studio." />}</div>
      </div>
      <div className="card"><h2>Try asking</h2><div className="chips">{EXAMPLES.map((e) => <button key={e} className="btn ghost sm" onClick={() => ask(e)}>{e}</button>)}</div></div>
    </div>
  );
}
