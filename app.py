import os
from pathlib import Path
import streamlit as st

from export_cursor_chat.cursor_to_md import (
    get_default_db_path,
    connect_readonly,
    get_cursor_disk_kv_rows,
    group_rows_by_type,
    parse_composer_row,
    parse_bubble_row,
    BubbleRow,
)


def _load_raw_store(db_path: Path):
    with connect_readonly(db_path) as conn:
        rows = get_cursor_disk_kv_rows(conn)
    return group_rows_by_type(rows)


def main():
    st.set_page_config(page_title="Cursor Chats", layout="wide")
    st.title("Cursor Chat Browser")

    env_path = os.getenv("CURSOR_CHAT_DB_PATH")
    default_db = Path(env_path) if env_path else get_default_db_path()
    db_path = st.text_input("Path to Cursor DB (state.vscdb)", value=str(default_db))

    if not db_path:
        st.stop()

    try:
        raw = _load_raw_store(Path(db_path))
    except Exception as e:
        st.error(f"Failed to load DB: {e}")
        st.stop()

    bubble_index: dict[tuple[str, str], BubbleRow] = {
        (b.composer_id, b.bubble_id): b for b in raw.bubbles
    }

    st.sidebar.header("Conversations")
    conversations: list[tuple[str, int]] = []
    for c_row in raw.composers:
        comp = parse_composer_row(c_row)
        if not comp:
            continue
        conversations.append((comp.name or "untitled", c_row.rowid))

    conversations.sort(key=lambda x: x[0].lower())
    options = [name for name, _ in conversations]
    selected = st.sidebar.selectbox("Select conversation", options=options)

    selected_row = next((c for c in raw.composers if (parse_composer_row(c) and (parse_composer_row(c).name or "untitled") == selected)), None)  # type: ignore[union-attr]
    if not selected_row:
        st.info("No conversations found.")
        st.stop()

    comp = parse_composer_row(selected_row)
    if not comp:
        st.warning("Invalid conversation data.")
        st.stop()

    st.header(comp.name or "untitled")
    for h in comp.full_conversation_headers_only:
        role = "User" if h.type == 1 else ("Assistant" if h.type == 2 else "Unknown")
        b_row = bubble_index.get((comp.composer_id, h.bubble_id))
        if not b_row:
            continue
        b = parse_bubble_row(b_row)
        if not b:
            continue

        if b.thinking_text is not None:
            with st.container():
                st.caption(f"{role} [thinking]")
                st.code(b.thinking_text)

        if b.text is not None:
            with st.container():
                st.caption(f"{role} [chat]")
                if role == "User":
                    # User inputs are plain text; avoid Markdown parsing issues
                    st.text(b.text)
                elif role == "Assistant":
                    # Assistant outputs are Markdown
                    st.markdown(b.text)
                else:
                    st.text(b.text)


if __name__ == "__main__":
    main()


