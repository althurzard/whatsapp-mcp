"""Draft/approval layer (Olaz-style): nothing is sent until the user approves a draft."""
import json, os, time, uuid, threading
from pathlib import Path

DRAFTS_FILE = Path(os.environ.get("WA_DRAFTS_FILE", Path(__file__).resolve().parent.parent / "drafts.json"))
MIN_GAP_SECONDS = 12  # anti-ban spacing between sends
_lock = threading.Lock()
_last_send = [0.0]


def _load():
    try:
        return json.loads(DRAFTS_FILE.read_text())
    except Exception:
        return {}


def _save(d):
    DRAFTS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def create(kind, recipient, text=None, media_path=None, note=None, mentions=None):
    with _lock:
        d = _load()
        did = uuid.uuid4().hex[:8]
        d[did] = {"draftId": did, "kind": kind, "recipient": recipient, "text": text,
                  "media_path": media_path, "note": note, "mentions": mentions or [], "state": "pending",
                  "created_at": time.time()}
        _save(d)
        return d[did]


def get(did):
    return _load().get(did)


def recent(limit=20):
    return sorted(_load().values(), key=lambda x: -x["created_at"])[:limit]


def set_state(did, state, **extra):
    with _lock:
        d = _load()
        if did in d:
            d[did].update(state=state, **extra)
            _save(d)
        return d.get(did)


def wait_gap():
    gap = MIN_GAP_SECONDS - (time.time() - _last_send[0])
    if gap > 0:
        time.sleep(gap)


def mark_sent_now():
    _last_send[0] = time.time()
