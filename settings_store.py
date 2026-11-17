import json
import os
from pathlib import Path
import keyring

APP_NAME = "ProductDiscoveryCopilot"
SERVICE = "ProductDiscoveryCopilot_OpenAI"
ACCOUNT = "OPENAI_API_KEY"
DEFAULT_MODEL = "gpt-5.4"

def app_dir():
    root = Path(os.getenv("APPDATA") or Path.home()) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root

def settings_path():
    return app_dir() / "settings.json"

def get_api_key():
    try:
        return keyring.get_password(SERVICE, ACCOUNT) or ""
    except Exception:
        return ""

def set_api_key(value):
    value = (value or "").strip()
    if value:
        keyring.set_password(SERVICE, ACCOUNT, value)
    else:
        try:
            keyring.delete_password(SERVICE, ACCOUNT)
        except Exception:
            pass

def load_settings():
    data = {"model": DEFAULT_MODEL, "reasoning_effort": "low"}
    p = settings_path()
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            data.update(loaded)
        except Exception:
            pass
    return data

def save_settings(model, reasoning_effort):
    payload = {"model": (model or DEFAULT_MODEL).strip(), "reasoning_effort": reasoning_effort}
    settings_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
