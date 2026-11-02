export default function Help() {
  const items = [
    ["AI Chat", "Without an API key the chat uses a clearly labeled rule-based demo, not a language model. Add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env, restart the backend and pick the provider."],
    ["NLP Lab", "Preprocessing, keywords, extractive summaries and the teaching demos work offline. Sentiment, zero-shot classification, abstractive summaries and entities need optional packages and a one-time model download."],
    ["Deep Learning Lab", "Trains a small neural network on the bundled digits dataset. Curves and metrics are measured during real training. Limits on epochs and time keep it quick."],
    ["Analytics Studio", "Upload .csv or .xlsx. Your original file is never modified: cleaning creates a new dataset after you preview the change. Data stays on your machine."],
    ["Troubleshooting", "'Cannot reach the backend' means the API is not running on port 8000. 'Model could not be loaded' means the optional model has not been downloaded. See the README."],
  ];
  return (
    <div className="stack"><h1>Help and documentation</h1>
      {items.map(([t, d]) => <div className="card" key={t}><h3>{t}</h3><p className="muted" style={{ margin: 0 }}>{d}</p></div>)}
      <p className="muted small">Full API reference: docs/API.md. Interactive API docs: http://localhost:8000/docs</p></div>
  );
}
