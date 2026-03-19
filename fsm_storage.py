# fsm_storage.py
import json
import os
from typing import Dict, Any

FSM_FILE = "fsm_state.json"

def load_fsm_data() -> Dict[str, Any]:
    if os.path.exists(FSM_FILE):
        try:
            with open(FSM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_fsm_data(data: Dict[str, Any]):
    with open(FSM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

_fsm_storage: Dict[str, Any] = {}

def _load_fsm():
    global _fsm_storage
    _fsm_storage = load_fsm_data()

def _save_fsm():
    save_fsm_data(_fsm_storage)
