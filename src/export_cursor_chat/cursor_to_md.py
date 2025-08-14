import os
import json
import sqlite3
import re
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from .utils import sanitize_filename


@dataclass
class DbEntry:
    rowid: int
    key: str
    value: str

@dataclass
class ComposerRow:
    rowid: int
    key: str
    composer_id: str
    raw_json: str

@dataclass
class BubbleRow:
    rowid: int
    key: str
    composer_id: str
    bubble_id: str
    raw_json: str

@dataclass
class MessageRequestContextRow:
    rowid: int
    key: str
    raw_json: str

@dataclass
class RawStore:
    composers: list[ComposerRow]
    bubbles: list[BubbleRow]
    message_request_contexts: list[MessageRequestContextRow]

@dataclass
class ComposerHeader:
    bubble_id: str
    type: int  # 1 user, 2 cursor

@dataclass
class ComposerData:
    key: str
    composer_id: str
    name: str
    full_conversation_headers_only: list[ComposerHeader]

@dataclass
class BubbleData:
    key: str
    composer_id: str
    bubble_id: str
    text: str | None
    thinking_text: str | None

@dataclass
class TextMessage:
    kind: Literal["text", "thinking"]
    content: str

@dataclass
class ChatSession:
    name: str
    messages: list[TextMessage]


def get_default_db_path() -> Path:
    """Return the default path to Cursor's SQLite state DB across OSes.

    Windows: %APPDATA%/Cursor/User/globalStorage/state.vscdb
    macOS:   ~/Library/Application Support/Cursor/User/globalStorage/state.vscdb
    Linux:   ~/.config/Cursor/User/globalStorage/state.vscdb

    This function does not check file existence; callers should handle errors.
    """
    system = platform.system()
    home = Path.home()
    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
        # Fallback if APPDATA is not set
        return home / "AppData" / "Roaming" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    # Assume Linux / other Unix
    return home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri_path = Path(db_path).as_posix()
    return sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True)


def get_cursor_disk_kv_rows(conn: sqlite3.Connection) -> list[DbEntry]:
    cursor = conn.execute(
        """
        SELECT rowid, [key], value
        FROM cursorDiskKV
        WHERE value IS NOT NULL AND value <> '[]'
        ORDER BY rowid;
        """
    )
    rows: list[DbEntry] = []
    for rowid, key, value in cursor.fetchall():
        rows.append(DbEntry(rowid, key, value))
    return rows


def _unwrap_v(obj: dict) -> dict:
    if isinstance(obj, dict) and "_v" in obj and "data" in obj and isinstance(obj.get("data"), dict):
        return obj["data"]
    return obj


def _parse_composer_id_from_key(key: str) -> str | None:
    # composerData:<id>
    m = re.match(r"^composerData:(?P<id>.+)$", key)
    if not m:
        return None
    cid = m.group("id").strip()
    return cid or None


def _parse_bubble_ids_from_key(key: str) -> tuple[str, str] | None:
    # bubbleId:<composerId>:<bubbleId>
    m = re.match(r"^bubbleId:(?P<cid>[^:]+):(?P<bid>.+)$", key)
    if not m:
        return None
    cid = m.group("cid").strip()
    bid = m.group("bid").strip()
    if not cid or not bid:
        return None
    return cid, bid


@dataclass
class CheckpointRow:
    rowid: int
    key: str
    raw_json: str


def group_rows_by_type(rows: list[DbEntry]) -> RawStore:
    composers: list[ComposerRow] = []
    bubbles: list[BubbleRow] = []
    mrcs: list[MessageRequestContextRow] = []
    checkpoints: list[CheckpointRow] = []

    for r in rows:
        key = r.key
        cid = _parse_composer_id_from_key(key)
        if cid:
            composers.append(ComposerRow(r.rowid, key, cid, r.value))
            continue
        ids = _parse_bubble_ids_from_key(key)
        if ids:
            bc, bb = ids
            bubbles.append(BubbleRow(r.rowid, key, bc, bb, r.value))
            continue
        if key.startswith("messageRequestContext:"):
            mrcs.append(MessageRequestContextRow(r.rowid, key, r.value))
            continue
        if key.startswith("checkpointId:"):
            checkpoints.append(CheckpointRow(r.rowid, key, r.value))

    # Extend RawStore with checkpoints without changing order of fields used elsewhere
    raw_store = RawStore(
        composers=composers,
        bubbles=bubbles,
        message_request_contexts=mrcs,
    )
    # Attach as attribute to keep API minimal while satisfying requirement to store all raws
    setattr(raw_store, "checkpoints", checkpoints)
    return raw_store


def parse_composer_row(row: ComposerRow) -> ComposerData | None:
    try:
        obj = json.loads(row.raw_json)
    except Exception:
        return None
    data = _unwrap_v(obj) if isinstance(obj, dict) else None
    if not isinstance(data, dict):
        return None
    name = str(data.get("name", ""))
    headers_raw = data.get("fullConversationHeadersOnly")
    headers: list[ComposerHeader] = []
    if isinstance(headers_raw, list):
        for h in headers_raw:
            if not isinstance(h, dict):
                continue
            bid = str(h.get("bubbleId", ""))
            if not bid:
                continue
            mtype = int(h.get("type", 0))
            headers.append(ComposerHeader(bubble_id=bid, type=mtype))
    if not headers:
        return None
    return ComposerData(
        key=row.key,
        composer_id=row.composer_id,
        name=name,
        full_conversation_headers_only=headers,
    )


def parse_bubble_row(row: BubbleRow) -> BubbleData | None:
    try:
        obj = json.loads(row.raw_json)
    except Exception:
        return None
    data = _unwrap_v(obj) if isinstance(obj, dict) else None
    if not isinstance(data, dict):
        return None
    text_val = data.get("text", "")
    text: str | None = None
    if isinstance(text_val, str) and text_val.strip() != "":
        text = text_val
    thinking_text: str | None = None
    thinking = data.get("thinking")
    if isinstance(thinking, dict):
        t = thinking.get("text")
        if isinstance(t, str) and t.strip() != "":
            thinking_text = t
    return BubbleData(
        key=row.key,
        composer_id=row.composer_id,
        bubble_id=row.bubble_id,
        text=text,
        thinking_text=thinking_text,
    )


def build_sessions(raw: RawStore) -> list[ChatSession]:
    bubble_index: dict[tuple[str, str], BubbleRow] = {
        (b.composer_id, b.bubble_id): b for b in raw.bubbles
    }
    sessions: list[ChatSession] = []
    for c_row in raw.composers:
        comp = parse_composer_row(c_row)
        if not comp:
            continue
        messages: list[TextMessage] = []
        for h in comp.full_conversation_headers_only:
            b_row = bubble_index.get((comp.composer_id, h.bubble_id))
            if not b_row:
                continue
            b = parse_bubble_row(b_row)
            if not b:
                continue
            if b.text is not None:
                messages.append(TextMessage(kind="text", content=b.text))
            if b.thinking_text is not None:
                messages.append(TextMessage(kind="thinking", content=b.thinking_text))
        if messages:
            sessions.append(ChatSession(name=comp.name, messages=messages))
    return sessions


def dump_rows_to_files(rows: list[DbEntry], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for entry in rows:
        base_name = sanitize_filename(entry.key)
        file_path = output_dir / f"{base_name}.json"
        data = json.loads(entry.value)
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

