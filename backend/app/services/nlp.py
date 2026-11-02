"""NLP tools. Classical tools use scikit-learn; model-based tools load Hugging Face models lazily."""
import re
from collections import Counter

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..core.config import env
from ..core.errors import AppError

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")
_pipes: dict = {}


def sentences(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if p.strip()]


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def _stemmer():
    try:
        from nltk.stem import PorterStemmer
        return PorterStemmer()
    except Exception:
        return None


def _lemmatizer():
    try:
        from nltk.stem import WordNetLemmatizer
        lem = WordNetLemmatizer()
        lem.lemmatize("tests")  # raises if the WordNet data is missing
        return lem
    except Exception:
        return None


def preprocess(text: str) -> dict:
    low = text.lower()
    toks = tokens(low)
    no_stop = [t for t in toks if t not in ENGLISH_STOP_WORDS]
    notes = []
    st, lem = _stemmer(), _lemmatizer()
    if st is None:
        notes.append("Stemming unavailable: install nltk (pip install nltk).")
    if lem is None:
        notes.append("Lemmatization unavailable: run  python -c \"import nltk; nltk.download('wordnet')\"")
    return {"characters": len(text), "words": len(tokens(text)), "sentence_count": len(sentences(text)),
            "sentences": sentences(text), "lowercased": low, "without_punctuation": re.sub(r"[^\w\s]", "", low),
            "tokens": toks, "tokens_without_stopwords": no_stop,
            "stems": [st.stem(t) for t in no_stop] if st else None,
            "lemmas": [lem.lemmatize(t) for t in no_stop] if lem else None, "notes": notes}


def _pipe(task: str, model: str, **kw):
    key = (task, model)
    if key not in _pipes:
        try:
            from transformers import pipeline
            _pipes[key] = pipeline(task, model=model, **kw)
        except ImportError:
            raise AppError(503, "dependency_missing",
                           "This tool needs the 'transformers' and 'torch' packages (see README).")
        except Exception:
            raise AppError(503, "model_unavailable",
                           f"Model '{model}' could not be loaded. It is downloaded on first use, which needs "
                           "internet access and disk space.")
    return _pipes[key]


def sentiment(text: str) -> dict:
    model = env("NEXORA_SENTIMENT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")
    res = _pipe("sentiment-analysis", model)(text, top_k=None, truncation=True)
    if res and isinstance(res[0], list):
        res = res[0]
    scores = sorted(({"label": r["label"].lower(), "score": round(float(r["score"]), 4)} for r in res),
                    key=lambda r: -r["score"])
    return {"model": model, "label": scores[0]["label"], "scores": scores,
            "note": "Scores are model probabilities, not certainty. Sarcasm and domain language often fool them."}


def classify(text: str, labels: list[str]) -> dict:
    model = env("NEXORA_ZEROSHOT_MODEL", "facebook/bart-large-mnli")
    r = _pipe("zero-shot-classification", model)(text, candidate_labels=labels, multi_label=False)
    return {"model": model, "results": [{"label": a, "score": round(float(b), 4)}
                                         for a, b in zip(r["labels"], r["scores"])]}


def summarize(text: str, method: str, n: int = 3) -> dict:
    sents = sentences(text)
    if method == "extractive":
        if len(sents) <= n:
            return {"method": "extractive", "summary": " ".join(sents),
                    "note": "The text is already short; returned unchanged."}
        scores = TfidfVectorizer(stop_words="english").fit_transform(sents).sum(axis=1).A1
        keep = sorted(sorted(range(len(sents)), key=lambda i: -scores[i])[:n])
        return {"method": "extractive", "summary": " ".join(sents[i] for i in keep),
                "note": "Extractive: the highest-scoring original sentences (TF-IDF), copied word for word."}
    model = env("NEXORA_SUMMARY_MODEL", "sshleifer/distilbart-cnn-12-6")
    pipe = _pipe("summarization", model)
    chunks, cur = [], ""
    for s in sents:  # chunk by ~3000 characters so long input fits the model window
        if len(cur) + len(s) > 3000 and cur:
            chunks.append(cur)
            cur = ""
        cur += s + " "
    chunks.append(cur)
    parts = [pipe(c, max_length=130, min_length=20, truncation=True)[0]["summary_text"] for c in chunks if c.strip()]
    return {"method": "abstractive", "model": model, "chunks": len(parts), "summary": " ".join(parts),
            "note": "Abstractive: new sentences written by a model. It can omit or distort facts; verify it."}


def keywords(text: str, top_k: int = 10) -> dict:
    docs = sentences(text) or [text]
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        m = vec.fit_transform(docs)
    except ValueError:
        raise AppError(400, "no_terms", "The text has no usable words after removing stop words.")
    sc = m.sum(axis=0).A1
    names = vec.get_feature_names_out()
    tfidf = [{"term": names[i], "score": round(float(sc[i]), 4)} for i in sc.argsort()[::-1][:top_k]]
    freq = Counter(t for t in tokens(text.lower()) if t not in ENGLISH_STOP_WORDS and len(t) > 1)
    return {"tfidf": tfidf, "frequency": [{"term": k, "count": v} for k, v in freq.most_common(top_k)],
            "note": "TF-IDF treats each sentence as a document, so with one sentence it equals plain frequency."}


def demo(mode: str, texts: list[str], n: int = 2) -> dict:
    texts = [t for t in texts if t.strip()]
    if not texts:
        raise AppError(400, "no_text", "Provide at least one non-empty text.")
    try:
        if mode in ("bow", "tfidf"):
            vec = CountVectorizer() if mode == "bow" else TfidfVectorizer()
            X = vec.fit_transform(texts).toarray().round(4).tolist()
            return {"vocabulary": list(vec.get_feature_names_out()), "matrix": X}
        if mode == "ngrams":
            tk = [t.lower() for t in tokens(texts[0])]
            n = max(1, min(n, 3))
            grams = Counter(" ".join(tk[i:i + n]) for i in range(len(tk) - n + 1))
            return {"n": n, "ngrams": [{"ngram": g, "count": c} for g, c in grams.most_common(30)]}
        if mode == "cosine":
            if len(texts) < 2:
                raise AppError(400, "need_two", "Cosine similarity needs at least two texts (one per line).")
            X = TfidfVectorizer().fit_transform(texts)
            return {"matrix": cosine_similarity(X).round(4).tolist()}
    except ValueError:
        raise AppError(400, "empty_vocabulary", "The text contains no usable words.")
    raise AppError(400, "invalid_mode", "Mode must be bow, tfidf, ngrams or cosine.")


def ner(text: str) -> dict:
    try:
        import spacy
        nlp = spacy.load(env("NEXORA_SPACY_MODEL", "en_core_web_sm"))
    except ImportError:
        raise AppError(503, "dependency_missing", "Named entity recognition needs spaCy (pip install spacy).")
    except OSError:
        raise AppError(503, "model_unavailable", "Run: python -m spacy download en_core_web_sm")
    return {"entities": [{"text": e.text, "label": e.label_} for e in nlp(text).ents]}
