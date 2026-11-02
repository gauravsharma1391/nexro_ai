import { ReactNode, useState } from "react";
import { Copy, Download, Play } from "lucide-react";
import { api } from "../api";
import { download, Spinner, useToast } from "../ui";

const SAMPLE = "Nexora makes data analysis approachable. The charts are clear and the summaries save time. However, the first setup was confusing. Overall the team built a useful and friendly tool.";

function Tool({ run, render, explain, sample = SAMPLE, top, multiline }: {
  run: (text: string) => Promise<any>; render: (r: any) => ReactNode; explain: string; sample?: string; top?: ReactNode; multiline?: boolean;
}) {
  const toast = useToast();
  const [text, setText] = useState("");
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true); setErr(""); setRes(null);
    try { setRes(await run(text)); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="stack">
      {top}
      <label>{multiline ? "Texts (one per line)" : "Input text"}<textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste or type text…" /></label>
      <div className="row">
        <button className="btn ghost" onClick={() => setText(sample)}>Use sample</button>
        <button className="btn" onClick={go} disabled={busy || !text.trim()}><Play size={14} /> Run</button>
        {busy && <Spinner />}
      </div>
      {err && <div className="err" role="alert">{err}</div>}
      {res && <div className="card stack">
        {render(res)}
        <div className="note">{explain}</div>
        <div className="row">
          <button className="btn ghost sm" onClick={() => { navigator.clipboard.writeText(JSON.stringify(res, null, 2)); toast("Copied"); }}><Copy size={12} /> Copy JSON</button>
          <button className="btn ghost sm" onClick={() => download("nlp-result.json", JSON.stringify(res, null, 2))}><Download size={12} /> Download</button>
        </div>
      </div>}
    </div>
  );
}

const Chips = ({ items }: { items: any[] | null }) => items ? <div className="chips">{items.map((t, i) => <span className="chip" key={i}>{String(t)}</span>)}</div> : null;
const Scores = ({ items }: { items: { label: string; score: number }[] }) => (
  <div className="stack">{items.map((s) => (
    <div key={s.label}><div className="row spread small"><span>{s.label}</span><span>{(s.score * 100).toFixed(1)}%</span></div><div className="bar"><i style={{ width: `${s.score * 100}%` }} /></div></div>
  ))}</div>
);
const Matrix = ({ cols, rows }: { cols?: string[]; rows: number[][] }) => (
  <div className="tablewrap"><table><thead><tr>{cols && <th />}{(cols || rows[0].map((_, i) => `doc ${i + 1}`)).map((c) => <th key={c}>{c}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{cols && <th>doc {i + 1}</th>}{r.map((v, j) => <td key={j}>{v}</td>)}</tr>)}</tbody></table></div>
);

function Preprocess() {
  return <Tool run={(t) => api("/api/nlp/preprocess", { method: "POST", json: { text: t } })}
    explain="Preprocessing cleans text so models can compare words. Stemming chops word endings (running → run); lemmatization maps words to dictionary forms (better → good)."
    render={(r) => <>
      <p className="small">{r.words} words · {r.characters} characters · {r.sentence_count} sentences</p>
      <h3>Tokens</h3><Chips items={r.tokens} /><h3>Without stop-words</h3><Chips items={r.tokens_without_stopwords} />
      <h3>Stems</h3>{r.stems ? <Chips items={r.stems} /> : <span className="muted small">unavailable</span>}
      <h3>Lemmas</h3>{r.lemmas ? <Chips items={r.lemmas} /> : <span className="muted small">unavailable</span>}
      {r.notes.map((n: string) => <div className="note" key={n}>{n}</div>)}</>} />;
}
const Sentiment = () => <Tool run={(t) => api("/api/nlp/sentiment", { method: "POST", json: { text: t } })}
  explain="The model estimates how likely the text is positive, neutral or negative. It can be wrong, especially with sarcasm, mixed opinions or unusual topics."
  render={(r) => <><h3>Prediction: {r.label}</h3><Scores items={r.scores} /><p className="muted small">Model: {r.model}</p></>} />;

function Classify() {
  const [labels, setLabels] = useState("billing, technical support, praise");
  return <Tool sample="My invoice shows a charge I do not recognise and I would like a refund."
    top={<label>Candidate labels (comma-separated)<input value={labels} onChange={(e) => setLabels(e.target.value)} /></label>}
    run={(t) => api("/api/nlp/classify", { method: "POST", json: { text: t, labels: labels.split(",").map((s) => s.trim()).filter(Boolean) } })}
    explain="Zero-shot classification scores how well the text fits each label you supply, without training on your labels. Scores across labels sum to 1."
    render={(r) => <><Scores items={r.results} /><p className="muted small">Model: {r.model}</p></>} />;
}
function Summarize() {
  const [method, setMethod] = useState("extractive");
  return <Tool top={<label>Method<select value={method} onChange={(e) => setMethod(e.target.value)}><option value="extractive">Extractive (works offline)</option><option value="abstractive">Abstractive (needs transformers model)</option></select></label>}
    run={(t) => api("/api/nlp/summarize", { method: "POST", json: { text: t, method } })}
    explain="Extractive summaries copy the most important sentences. Abstractive summaries are newly written by a model and may contain mistakes."
    render={(r) => <><span className="badge">{r.method}</span><p>{r.summary}</p><p className="muted small">{r.note}</p></>} />;
}
const Keywords = () => <Tool run={(t) => api("/api/nlp/keywords", { method: "POST", json: { text: t } })}
  explain="TF-IDF rewards words that are frequent in some sentences but not everywhere. Raw frequency just counts."
  render={(r) => <><h3>TF-IDF</h3><Chips items={r.tfidf.map((k: any) => `${k.term} (${k.score})`)} /><h3>Frequency</h3><Chips items={r.frequency.map((k: any) => `${k.term} ×${k.count}`)} /><p className="muted small">{r.note}</p></>} />;

function Concepts() {
  const [mode, setMode] = useState("bow");
  const [n, setN] = useState(2);
  return <div className="stack">
    <Tool multiline sample={"the cat sat on the mat\nthe dog sat on the log\nstock markets rallied today"}
      top={<div className="row"><label>Demo<select value={mode} onChange={(e) => setMode(e.target.value)}><option value="bow">Bag of Words</option><option value="tfidf">TF-IDF</option><option value="ngrams">N-grams</option><option value="cosine">Cosine similarity</option></select></label>
        {mode === "ngrams" && <label>n<select value={n} onChange={(e) => setN(+e.target.value)}>{[1, 2, 3].map((v) => <option key={v}>{v}</option>)}</select></label>}</div>}
      run={(t) => api("/api/nlp/demo", { method: "POST", json: { mode, texts: t.split("\n"), n } })}
      explain={{ bow: "Bag of Words counts each word per document and ignores order.", tfidf: "TF-IDF down-weights words found in many documents.", ngrams: "N-grams are runs of n consecutive words, capturing a little word order.", cosine: "Cosine similarity compares document directions: 1 means the same word mix, 0 means nothing shared." }[mode]!}
      render={(r) => r.ngrams ? <Chips items={r.ngrams.map((g: any) => `${g.ngram} ×${g.count}`)} />
        : r.vocabulary ? <Matrix cols={r.vocabulary} rows={r.matrix} /> : <Matrix rows={r.matrix} />} />
    <div className="card"><h3>Named entities</h3>
      <Tool sample="Ada Lovelace worked with Charles Babbage in London in 1843." run={(t) => api("/api/nlp/ner", { method: "POST", json: { text: t } })}
        explain="Named Entity Recognition tags people, places, organizations and dates. It needs spaCy and its small English model." render={(r) => <Chips items={r.entities.map((e: any) => `${e.text} (${e.label})`)} />} /></div>
    <div className="card"><h3>Embedding ideas</h3><p className="muted small" style={{ margin: 0 }}>Word embeddings place words as points in space so similar meanings sit close together. Word2Vec learns them by predicting a word from its neighbors (CBOW) or neighbors from a word (skip-gram, which pairs a word with each nearby context word). GloVe learns from global word co-occurrence counts. These need large pretrained vectors, so this lab explains them rather than faking results.</p></div>
  </div>;
}

const TABS: [string, () => JSX.Element][] = [["Preprocessing", Preprocess], ["Sentiment", Sentiment], ["Classification", Classify], ["Summarization", Summarize], ["Keywords", Keywords], ["Concepts & NER", Concepts]];
export default function NLPLab() {
  const [tab, setTab] = useState(0);
  const Active = TABS[tab][1];
  return <div className="stack"><div><h1>NLP Lab</h1><p className="sub">Every result comes from a real run. Tools that need a model say so when it is missing.</p></div>
    <div className="tabs" role="tablist">{TABS.map(([l], i) => <button key={l} role="tab" aria-selected={tab === i} className={`tab ${tab === i ? "on" : ""}`} onClick={() => setTab(i)}>{l}</button>)}</div>
    <Active key={tab} /></div>;
}
