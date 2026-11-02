import { useEffect, useRef, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, upload } from "../api";
import { Empty, Spinner, useToast } from "../ui";

const CONCEPTS: [string, string][] = [
  ["Neurons and activations", "A neuron multiplies inputs by weights, adds a bias and passes the result through an activation function such as ReLU, sigmoid or tanh. Activations let networks learn curved, non-linear patterns."],
  ["CNNs", "Convolutional networks slide small filters over an image to detect edges, then shapes, then objects. Pooling shrinks the image while keeping the strongest signals."],
  ["RNNs and LSTMs", "Recurrent networks read a sequence one step at a time while carrying a memory. LSTMs add gates that decide what to keep or forget, helping with long sequences."],
  ["Transformers and attention", "Attention lets every word look at every other word and weigh how relevant it is. Transformers stack this idea and power modern language models."],
  ["Overfitting vs underfitting", "Underfitting: both training and validation scores are poor. Overfitting: training keeps improving while validation stops improving or worsens. Try a very large network with many epochs below and watch the gap."],
  ["Hyperparameters", "Learning rate is the step size (too high is unstable, too low is slow). Batch size is how many examples per update. Epochs are full passes over the training data."],
];
const act = Array.from({ length: 41 }, (_, i) => { const x = (i - 20) / 4; return { x, relu: Math.max(0, x), sigmoid: 1 / (1 + Math.exp(-x)), tanh: Math.tanh(x) }; });

export default function DeepLearningLab() {
  const toast = useToast();
  const [p, setP] = useState({ hidden: 32, lr: 0.01, batch: 32, epochs: 20 });
  const [job, setJob] = useState<any>(null);
  const [err, setErr] = useState("");
  const [sample, setSample] = useState<any>(null);
  const [pred, setPred] = useState<any>(null);
  const timer = useRef<number>();

  const poll = (id: string) => {
    api(`/api/deep-learning/jobs/${id}`).then((j) => { setJob(j); if (j.status === "running") timer.current = window.setTimeout(() => poll(id), 700); })
      .catch((e) => setErr(e.message));
  };
  useEffect(() => () => clearTimeout(timer.current), []);
  const train = async () => {
    setErr(""); setSample(null); setPred(null);
    try { const { job_id } = await api("/api/deep-learning/train", { method: "POST", json: p }); poll(job_id); } catch (e: any) { setErr(e.message); }
  };
  const getSample = () => api("/api/deep-learning/sample").then(setSample).catch((e) => toast(e.message, "err"));
  const onFile = async (f?: File) => {
    if (!f) return;
    try { setPred(await upload("/api/deep-learning/predict", f)); } catch (e: any) { toast(e.message, "err"); }
  };
  const field = (k: keyof typeof p, label: string, step = 1) => (
    <label>{label}<input type="number" step={step} value={p[k]} onChange={(e) => setP({ ...p, [k]: Number(e.target.value) })} /></label>);
  const running = job?.status === "running";

  return (
    <div className="stack">
      <div><h1>Deep Learning Lab</h1><p className="sub">Train a small neural network on 1,797 real 8×8 handwritten digits. Nothing here is pre-recorded.</p></div>
      <div className="card stack"><h2>1. Train</h2>
        <div className="grid g4">{field("hidden", "Hidden neurons (2–256)")}{field("lr", "Learning rate", 0.001)}{field("batch", "Batch size (8–256)")}{field("epochs", "Epochs (1–100)")}</div>
        <div className="row"><button className="btn" onClick={train} disabled={running}>Start training</button>{running && <><Spinner /><span>{Math.round((job.progress || 0) * 100)}%</span></>}</div>
        {err && <div className="err" role="alert">{err}</div>}
        {job?.status === "failed" && <div className="err">{job.error}</div>}
        {job?.note && <div className="note">{job.note}</div>}
        {job?.history?.length > 0 && <>
          <div className="grid g2">
            {[["Loss (lower is better)", "train_loss", "val_loss"], ["Accuracy", "train_acc", "val_acc"]].map(([t, a, b]) => (
              <div key={t}><h3>{t}</h3><div style={{ height: 240 }}><ResponsiveContainer><LineChart data={job.history}><CartesianGrid stroke="var(--line)" /><XAxis dataKey="epoch" stroke="var(--muted)" /><YAxis stroke="var(--muted)" domain={a.includes("acc") ? [0, 1] : ["auto", "auto"]} /><Tooltip /><Legend />
                <Line dataKey={a} name="training" stroke="#5cc8f2" dot={false} /><Line dataKey={b} name="validation" stroke="#b79cff" dot={false} /></LineChart></ResponsiveContainer></div></div>))}
          </div>
          {job.status === "done" && <p>Validation accuracy: <b>{(job.test_accuracy * 100).toFixed(1)}%</b> on {Math.round(1797 * 0.25)} held-out images.</p>}
          <div className="note">If training loss keeps falling while validation loss rises, the network is memorizing (overfitting). Try changing the settings and compare.</div>
        </>}
        {job?.confusion && <details><summary>Confusion matrix (rows: actual, columns: predicted)</summary>
          <div className="tablewrap"><table><thead><tr><th />{job.confusion.map((_: any, i: number) => <th key={i}>{i}</th>)}</tr></thead>
            <tbody>{job.confusion.map((r: number[], i: number) => <tr key={i}><th>{i}</th>{r.map((v, j) => <td key={j} style={{ background: v && i === j ? "color-mix(in srgb,var(--ok) 25%,transparent)" : v ? "color-mix(in srgb,var(--danger) 25%,transparent)" : undefined }}>{v}</td>)}</tr>)}</tbody></table></div></details>}
      </div>
      <div className="card stack"><h2>2. Try the trained model</h2>
        <div className="row"><button className="btn" onClick={getSample}>Test on a random held-out digit</button>
          <label style={{ flexDirection: "row", alignItems: "center" }}>or upload a PNG/JPEG of a dark digit on white<input type="file" accept="image/png,image/jpeg" onChange={(e) => onFile(e.target.files?.[0])} /></label></div>
        {!job?.test_accuracy && !sample && !pred && <Empty title="Train a model first" hint="Predictions need a model trained in this session." />}
        {sample && <div className="row">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(8,22px)", gap: 1 }}>{sample.pixels.flat().map((v: number, i: number) => <div key={i} style={{ width: 22, height: 22, background: `rgb(${v * 16},${v * 16},${v * 16})` }} />)}</div>
          <div><p>Actual: <b>{sample.actual}</b> · Predicted: <b>{sample.predicted}</b> {sample.actual === sample.predicted ? "✓" : "✗"}</p>
            <div className="chips">{sample.probabilities.map((x: any) => <span className="chip" key={x.digit}>{x.digit}: {(x.probability * 100).toFixed(1)}%</span>)}</div></div></div>}
        {pred && <div><p>Predicted digit: <b>{pred.predicted}</b></p><div className="chips">{pred.probabilities.map((x: any) => <span className="chip" key={x.digit}>{x.digit}: {(x.probability * 100).toFixed(1)}%</span>)}</div><div className="note" style={{ marginTop: 8 }}>{pred.note}</div></div>}
      </div>
      <div className="card"><h2>Activation functions (computed from their formulas)</h2><div style={{ height: 220 }}><ResponsiveContainer><LineChart data={act}><CartesianGrid stroke="var(--line)" /><XAxis dataKey="x" stroke="var(--muted)" /><YAxis stroke="var(--muted)" /><Tooltip /><Legend />
        <Line dataKey="relu" stroke="#5cc8f2" dot={false} /><Line dataKey="sigmoid" stroke="#b79cff" dot={false} /><Line dataKey="tanh" stroke="#5fd6a0" dot={false} /></LineChart></ResponsiveContainer></div></div>
      <div className="grid g2">{CONCEPTS.map(([t, d]) => <div className="card" key={t}><h3>{t}</h3><p className="muted small" style={{ margin: 0 }}>{d}</p></div>)}</div>
      <p className="muted small">Not included: pretrained ImageNet/CNN inference (needs torch + large weights). The training code lives in backend/app/services/dl.py.</p>
    </div>
  );
}
