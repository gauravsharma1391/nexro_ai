from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..core import db
from ..core.config import settings
from ..core.errors import AppError
from ..schemas import ChatRequest, RenameRequest
from ..services import llm

router = APIRouter(prefix="/api")


@router.post("/chat")
def chat(req: ChatRequest):
    provider = req.provider or llm.default_provider()
    if not req.regenerate:
        if not req.message or not req.message.strip():
            raise AppError(422, "empty_message", "Message cannot be empty.")
        if len(req.message) > settings.max_message_chars:
            raise AppError(413, "message_too_long", f"Messages are limited to {settings.max_message_chars} characters.")
    if req.conversation_id:
        if not db.get_conversation(req.conversation_id):
            raise AppError(404, "conversation_not_found", "Conversation not found.")
        cid = req.conversation_id
    else:
        if req.regenerate:
            raise AppError(422, "nothing_to_regenerate", "Nothing to regenerate.")
        cid = db.create_conversation(req.message.strip()[:50])
    if req.regenerate:
        db.delete_last_assistant(cid)
    else:
        db.add_message(cid, "user", req.message.strip())
    history = [{"role": m["role"], "content": m["content"]} for m in db.get_messages(cid)][-settings.context_messages:]
    stream = llm.open_stream(provider, history)  # raises a readable error before streaming starts

    def gen():
        parts: list[str] = []
        try:
            for chunk in stream:
                parts.append(chunk)
                yield chunk
        finally:  # also runs when the user presses Stop, so partial answers are kept
            text = "".join(parts)
            if text:
                db.add_message(cid, "assistant", text, provider)

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8",
                             headers={"X-Conversation-Id": cid, "X-Provider": provider})


@router.get("/conversations")
def list_conversations():
    return db.list_conversations()


@router.get("/conversations/{cid}")
def get_conversation(cid: str):
    conv = db.get_conversation(cid)
    if not conv:
        raise AppError(404, "conversation_not_found", "Conversation not found.")
    return {**conv, "messages": db.get_messages(cid)}


@router.patch("/conversations/{cid}")
def rename(cid: str, body: RenameRequest):
    if not db.rename_conversation(cid, body.title.strip()):
        raise AppError(404, "conversation_not_found", "Conversation not found.")
    return {"ok": True}


@router.delete("/conversations/{cid}")
def delete(cid: str):
    if not db.delete_conversation(cid):
        raise AppError(404, "conversation_not_found", "Conversation not found.")
    return {"ok": True}
