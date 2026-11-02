import importlib.util

from fastapi import APIRouter

from ..core import db
from ..core.config import settings
from ..services import dl, llm

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@router.get("/stats")
def stats():
    return db.stats()  # real counts from stored data


@router.get("/models")
def models():
    has = lambda m: importlib.util.find_spec(m) is not None  # noqa: E731
    return {
        "providers": llm.providers(), "default_provider": llm.default_provider(),
        "limits": {"max_message_chars": settings.max_message_chars, "context_messages": settings.context_messages,
                   "request_timeout_seconds": settings.request_timeout, "max_upload_mb": settings.max_upload_mb,
                   "max_rows": settings.max_rows, "max_train_seconds": settings.max_train_seconds},
        "optional_dependencies": {"transformers": has("transformers"), "torch": has("torch"), "nltk": has("nltk"),
                                  "spacy": has("spacy"), "pillow": has("PIL"), "openpyxl": has("openpyxl")},
        "deep_learning": dl.status()}
