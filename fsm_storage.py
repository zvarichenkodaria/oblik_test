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


async def ensure_fsm_data(user_id: int) -> Dict[str, Any]:
    uid = str(user_id)
    if uid not in _fsm_storage:
        _fsm_storage[uid] = {
            "state": None,
            "data": {},
        }
    return _fsm_storage[uid]


async def update_fsm_data(user_id: int, **data):
    fs = await ensure_fsm_data(user_id)
    fs["data"].update(data)
    _save_fsm()


async def set_fsm_state(user_id: int, state: str):
    fs = await ensure_fsm_data(user_id)
    fs["state"] = state
    _save_fsm()


async def get_fsm_data(user_id: int) -> Dict[str, Any]:
    fs = await ensure_fsm_data(user_id)
    return fs["data"]


async def get_fsm_state(user_id: int) -> str | None:
    fs = await ensure_fsm_data(user_id)
    return fs["state"]
