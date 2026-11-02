"""Small, real neural-network experiments (scikit-learn MLP on the bundled 8x8 digits dataset).
Training runs in a background thread with a time limit; every curve point is measured, never invented."""
import io
import logging
import random
import threading
import time
import uuid

import numpy as np

from ..core.config import settings
from ..core.errors import AppError

log = logging.getLogger("nexora.dl")
_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_model: dict = {"clf": None, "meta": None}
_data = None
LIMITS = {"hidden": (2, 256), "lr": (0.0001, 0.5), "batch": (8, 256), "epochs": (1, 100)}


def _dataset():
    global _data
    if _data is None:
        from sklearn.datasets import load_digits
        from sklearn.model_selection import train_test_split
        d = load_digits()
        _data = train_test_split(d.data / 16.0, d.target, test_size=0.25, stratify=d.target, random_state=0)
    return _data


def start_training(hidden: int, lr: float, batch: int, epochs: int) -> str:
    for k, v in (("hidden", hidden), ("lr", lr), ("batch", batch), ("epochs", epochs)):
        lo, hi = LIMITS[k]
        if not lo <= v <= hi:
            raise AppError(422, "invalid_parameter", f"{k} must be between {lo} and {hi}.")
    with _lock:
        if any(j["status"] == "running" for j in _jobs.values()):
            raise AppError(409, "job_running", "A training job is already running. Wait for it to finish.")
        jid = uuid.uuid4().hex
        _jobs[jid] = {"id": jid, "status": "running", "params": {"hidden": hidden, "lr": lr, "batch": batch,
                      "epochs": epochs}, "history": [], "progress": 0.0, "error": None, "note": None,
                      "test_accuracy": None, "confusion": None, "started": time.time()}
        for old in list(_jobs)[:-20]:
            _jobs.pop(old, None)
    threading.Thread(target=_train, args=(jid,), daemon=True).start()
    return jid


def _train(jid: str) -> None:
    job = _jobs[jid]
    try:
        from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
        from sklearn.neural_network import MLPClassifier
        Xtr, Xte, ytr, yte = _dataset()
        p = job["params"]
        clf = MLPClassifier(hidden_layer_sizes=(p["hidden"],), learning_rate_init=p["lr"], solver="adam",
                            random_state=0)
        classes, rng = np.arange(10), np.random.default_rng(0)
        for ep in range(1, p["epochs"] + 1):
            if time.time() - job["started"] > settings.max_train_seconds:
                job["note"] = f"Stopped after {ep - 1} epochs: time limit of {settings.max_train_seconds}s reached."
                break
            idx = rng.permutation(len(Xtr))
            for s in range(0, len(idx), p["batch"]):
                b = idx[s:s + p["batch"]]
                clf.partial_fit(Xtr[b], ytr[b], classes=classes)
            tp, vp = clf.predict_proba(Xtr), clf.predict_proba(Xte)
            job["history"].append({
                "epoch": ep, "train_loss": float(log_loss(ytr, tp, labels=classes)),
                "val_loss": float(log_loss(yte, vp, labels=classes)),
                "train_acc": float(accuracy_score(ytr, tp.argmax(1))),
                "val_acc": float(accuracy_score(yte, vp.argmax(1)))})
            job["progress"] = ep / p["epochs"]
        if not job["history"]:
            raise RuntimeError("no epochs completed")
        vp = clf.predict_proba(Xte)
        job["test_accuracy"] = job["history"][-1]["val_acc"]
        job["confusion"] = confusion_matrix(yte, vp.argmax(1), labels=classes).tolist()
        _model.update(clf=clf, meta={"job_id": jid, **p, "test_accuracy": job["test_accuracy"]})
        job["status"] = "done"
    except Exception:
        log.exception("training failed")
        job["status"], job["error"] = "failed", "Training failed. Check the server log for details."


def get_job(jid: str) -> dict:
    j = _jobs.get(jid)
    if not j:
        raise AppError(404, "job_not_found", "Training job not found.")
    return {k: v for k, v in j.items() if k != "started"}


def status() -> dict:
    return {"trained": _model["clf"] is not None, "model": _model["meta"],
            "dataset": "scikit-learn digits (1,797 images, 8x8 pixels, 10 classes)"}


def _need_model():
    if _model["clf"] is None:
        raise AppError(409, "no_model", "No trained model yet. Train one first in the Deep Learning Lab.")
    return _model["clf"]


def _probs(clf, x: np.ndarray) -> list[dict]:
    p = clf.predict_proba(x.reshape(1, -1))[0]
    return [{"digit": int(i), "probability": round(float(v), 4)} for i, v in sorted(enumerate(p), key=lambda t: -t[1])]


def sample() -> dict:
    clf = _need_model()
    _, Xte, _, yte = _dataset()
    i = random.randrange(len(Xte))
    pr = _probs(clf, Xte[i])
    return {"pixels": (Xte[i] * 16).round().astype(int).reshape(8, 8).tolist(), "actual": int(yte[i]),
            "predicted": pr[0]["digit"], "probabilities": pr[:5]}


def predict_image(content: bytes, invert: bool = True) -> dict:
    clf = _need_model()
    if len(content) > 2 * 1024 * 1024:
        raise AppError(413, "too_large", "Image must be 2 MB or smaller.")
    try:
        from PIL import Image
    except ImportError:
        raise AppError(503, "dependency_missing", "Image prediction needs Pillow (pip install pillow).")
    try:
        img = Image.open(io.BytesIO(content))
        if img.format not in ("PNG", "JPEG"):
            raise ValueError
        img = img.convert("L").resize((8, 8), Image.LANCZOS)
    except Exception:
        raise AppError(400, "invalid_image", "Upload a valid PNG or JPEG image.")
    x = np.asarray(img, dtype=float) / 255.0
    if invert:
        x = 1.0 - x  # the dataset is light ink on a dark background
    pr = _probs(clf, x.reshape(-1))
    return {"predicted": pr[0]["digit"], "probabilities": pr[:5],
            "note": "The model only knows 8x8 handwritten digits; photos or other objects give meaningless results."}
