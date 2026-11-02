"""LLM provider abstraction. Keys are read from environment variables and never leave the backend."""
import json
import urllib.error
import urllib.request

from ..core.config import env, settings
from ..core.errors import AppError


def providers() -> list[dict]:
    base = env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    custom_base = "api.openai.com" not in base  # e.g. a local Ollama / LM Studio / vLLM server
    return [
        {"id": "openai_compatible", "label": "OpenAI-compatible API", "kind": "external",
         "model": env("OPENAI_MODEL", "gpt-4o-mini"), "ready": bool(env("OPENAI_API_KEY")) or custom_base,
         "hint": "Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL / OPENAI_MODEL) in .env"},
        {"id": "anthropic", "label": "Anthropic Claude", "kind": "external",
         "model": env("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "ready": bool(env("ANTHROPIC_API_KEY")),
         "hint": "Set ANTHROPIC_API_KEY (and optionally ANTHROPIC_MODEL) in .env"},
        {"id": "demo", "label": "Local demo (rule-based, not an LLM)", "kind": "demo", "model": "none",
         "ready": True, "hint": "Always available. Answers a few built-in questions only."},
    ]


def default_provider() -> str:
    wanted = env("LLM_PROVIDER")
    ps = providers()
    if wanted and any(p["id"] == wanted and p["ready"] for p in ps):
        return wanted
    return next((p["id"] for p in ps if p["kind"] == "external" and p["ready"]), "demo")


def _post(url: str, headers: dict, payload: dict):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        return urllib.request.urlopen(req, timeout=settings.request_timeout)
    except urllib.error.HTTPError as e:
        msg = {401: "The provider rejected the API key.", 403: "The provider denied access to this model.",
               404: "Model or endpoint not found. Check the model name and base URL.",
               429: "The provider's rate limit or quota was reached. Try again later."}.get(
            e.code, f"The provider returned HTTP {e.code}.")
        raise AppError(502, "provider_error", msg)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AppError(504, "provider_unreachable", "Could not reach the provider (network error or timeout).")


def _sse(resp):
    for raw in resp:
        line = raw.decode("utf-8", "ignore").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            return
        try:
            yield json.loads(data)
        except json.JSONDecodeError:
            continue


def _openai(messages: list[dict]):
    base = env("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    headers = {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"} if env("OPENAI_API_KEY") else {}
    resp = _post(f"{base}/chat/completions", headers, {
        "model": env("OPENAI_MODEL", "gpt-4o-mini"), "stream": True,
        "messages": [{"role": "system", "content": settings.system_prompt}] + messages})

    def gen():
        with resp:
            for ev in _sse(resp):
                try:
                    t = ev["choices"][0]["delta"].get("content")
                except (KeyError, IndexError, TypeError, AttributeError):
                    t = None
                if t:
                    yield t
    return gen()


def _anthropic(messages: list[dict]):
    resp = _post("https://api.anthropic.com/v1/messages",
                 {"x-api-key": env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"},
                 {"model": env("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 2048, "stream": True,
                  "system": settings.system_prompt, "messages": messages})

    def gen():
        with resp:
            for ev in _sse(resp):
                if ev.get("type") == "content_block_delta":
                    t = ev.get("delta", {}).get("text")
                    if t:
                        yield t
    return gen()


def _demo(messages: list[dict]):
    q = messages[-1]["content"].lower() if messages else ""
    head = "**Local demo mode.** This reply comes from a tiny rule-based helper, *not* a language model.\n\n"
    if q.strip() in ("hi", "hello", "hey") or q.startswith(("hello", "hi ", "hey ")):
        body = "Hello! I can point you to the right Nexora module."
    elif "csv" in q or "data" in q or "analy" in q:
        body = "Open **Analytics Studio** to upload a CSV/XLSX, see statistics, build charts and clean data."
    elif any(w in q for w in ("sentiment", "summar", "nlp", "keyword")):
        body = "The **NLP Lab** has preprocessing, sentiment, classification, summarization and keyword tools."
    elif any(w in q for w in ("neural", "deep", "train")):
        body = "The **Deep Learning Lab** trains a small neural network on the digits dataset and shows real curves."
    else:
        body = ("I can't answer open-ended questions without a real model. Add an API key in `.env` "
                "(see README) and choose that provider, or use the other modules.")
    return iter([w + " " for w in (head + body).split(" ")])


def open_stream(provider_id: str, messages: list[dict]):
    """Opens the provider connection eagerly so errors surface before streaming starts."""
    info = next((p for p in providers() if p["id"] == provider_id), None)
    if not info:
        raise AppError(400, "unknown_provider", f"Unknown provider '{provider_id}'.")
    if not info["ready"]:
        raise AppError(409, "provider_not_ready", f"{info['label']} is not configured. {info['hint']}")
    if provider_id == "demo":
        return _demo(messages)
    return _openai(messages) if provider_id == "openai_compatible" else _anthropic(messages)
