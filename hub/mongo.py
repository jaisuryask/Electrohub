"""MongoDB storage for chat logs and feedback.

Set MONGODB_URI (e.g. a free MongoDB Atlas cluster) in the environment. If it is missing or the
server is unreachable, documents are appended to a local JSONL file instead so the site never breaks;
the Health page shows which store is in use.
"""
import json
import os
import time
import uuid
from pathlib import Path

_client = None
FALLBACK_DIR = Path(__file__).resolve().parent.parent / ".fallback"


def configured():
    return bool(os.environ.get("MONGODB_URI"))


def _db():
    global _client
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        return None
    if _client is None:
        from pymongo import MongoClient

        _client = MongoClient(uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500, socketTimeoutMS=4000)
    return _client[os.environ.get("MONGODB_DB", "electrolab")]


def insert(collection, doc):
    """Store a document. Returns (id, store) where store is 'mongodb' or 'fallback-file'."""
    doc = {**doc, "ts": time.time()}
    try:
        db = _db()
        if db is not None:
            return str(db[collection].insert_one(doc).inserted_id), "mongodb"
    except Exception:
        pass
    doc.pop("_id", None)
    new_id = "local-" + uuid.uuid4().hex[:12]
    try:
        FALLBACK_DIR.mkdir(exist_ok=True)
        with open(FALLBACK_DIR / f"{collection}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({**doc, "_id": new_id}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return new_id, "fallback-file"


def update_feedback(log_id, fields):
    """Attach feedback to a chat-log document (best effort)."""
    try:
        db = _db()
        if db is not None and not str(log_id).startswith("local-"):
            from bson import ObjectId

            db["chat_logs"].update_one({"_id": ObjectId(log_id)}, {"$set": {"feedback": fields}})
    except Exception:
        pass


def ping():
    """Health probe -> dict(ok, detail)."""
    if not configured():
        return {"ok": False, "detail": "MONGODB_URI not set (using local fallback file)"}
    try:
        _db().command("ping")
        return {"ok": True, "detail": "connected"}
    except Exception as exc:
        return {"ok": False, "detail": f"unreachable ({type(exc).__name__})"}
