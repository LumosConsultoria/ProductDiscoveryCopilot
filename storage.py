import json
import os
import re
import uuid
from pathlib import Path
from datetime import datetime

APP_NAME = "ProductDiscoveryCopilot"

def app_dir():
    root = Path(os.getenv("APPDATA") or Path.home()) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root

def data_dir():
    path = app_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path

def index_file():
    return data_dir() / "index.json"

def _slug(text):
    text = (text or "discovery").lower().strip()
    text = re.sub(r"[^a-z0-9à-ÿ]+", "-", text, flags=re.IGNORECASE)
    return text.strip("-")[:50] or "discovery"

def _read_index():
    p = index_file()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def _write_index(items):
    index_file().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def _validate_discovery_id(discovery_id):
    """Reject path separators and traversal in user-supplied discovery identifiers."""
    if not isinstance(discovery_id, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}", discovery_id):
        raise ValueError("Invalid discovery ID")
    return discovery_id


def save_discovery(title, context, evidence, messages, stage="Em andamento", discovery_id=None):
    if discovery_id:
        discovery_id = _validate_discovery_id(discovery_id)
    if not discovery_id:
        discovery_id = f"{_slug(title)}-{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat(timespec="seconds")
    p = data_dir() / f"{discovery_id}.json"
    created_at = now
    if p.exists():
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            created_at = old.get("created_at", now)
        except Exception:
            pass
    payload = {
        "id": discovery_id, "title": title, "context": context, "evidence": evidence,
        "messages": messages, "stage": stage, "created_at": created_at, "updated_at": now,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    idx = [x for x in _read_index() if x.get("id") != discovery_id]
    idx.insert(0, {"id": discovery_id, "title": title, "stage": stage, "updated_at": now})
    _write_index(idx[:200])
    return payload

def list_discoveries():
    return _read_index()

def load_discovery(discovery_id):
    discovery_id = _validate_discovery_id(discovery_id)
    p = data_dir() / f"{discovery_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
