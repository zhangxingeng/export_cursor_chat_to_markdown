# Export Your Cursor Chat to Markdown, HTML or Directly View with Streamlit

Export your Cursor editor chat history to Markdown or HTML, or browse it in a Streamlit UI.

### Features

- Export to Markdown (.md)
- Export to HTML (.html) styled with Tailwind CSS
- Interactive Streamlit UI to browse conversations

### Install (Super simple)

Use uv/pip to install in editable mode for development:

```bash
uv sync
```

If you are overwhelmed by the details, and not sure what does any of this means, then just run:

```bash
export-cursor-chat ui
```

That's It! Enjoy 😊

### Advanced Usage (CLI)

```bash
# Show help (How do I use this?)
export-cursor-chat --help

# Export Markdown (You want to see it in markdown format)
export-cursor-chat markdown --out-dir chat_output_md

# Export HTML (You want to see it in html format)
export-cursor-chat html --out-dir chat_output_html

# Launch UI via Streamlit (You want to see it in a website fashion)
export-cursor-chat ui

# Use a specific DB path (Windows)
export-cursor-chat markdown --db-path "C:\\Users\\<you>\\AppData\\Roaming\\Cursor\\User\\globalStorage\\state.vscdb"

# Use a specific DB path (macOS)
export-cursor-chat markdown --db-path "/Users/$USER/Library/Application Support/Cursor/User/globalStorage/state.vscdb"

# Use a specific DB path (Linux)
export-cursor-chat markdown --db-path "$HOME/.config/Cursor/User/globalStorage/state.vscdb"
```

Notes:

- The tool auto-detects the default DB path across Windows, macOS, and Linux. If omitted, it tries these locations:
  - Windows: `%APPDATA%/Cursor/User/globalStorage/state.vscdb`
  - macOS: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
  - Linux: `~/.config/Cursor/User/globalStorage/state.vscdb`
- If you keep multiple Cursor profiles or the DB is elsewhere, pass `--db-path` explicitly (works for `markdown`, `html`, and `ui`).
- You can dump raw JSON rows for debugging with `--dump-raw <dir>`.

### Advanced: Streamlit UI

You can also run the Streamlit app directly:

```bash
streamlit run app.py
```

Optionally set an environment variable to point at a specific DB:

```bash
set CURSOR_CHAT_DB_PATH=C:\\path\\to\\state.vscdb  # PowerShell: $env:CURSOR_CHAT_DB_PATH = "..."
```

### Library structure

- `src/export_cursor_chat/cursor_to_md.py`: SQLite read-only access, parsing into dataclasses, session building, utility dumps.
- `src/export_cursor_chat/to_markdown.py`: Markdown generation and export.
- `src/export_cursor_chat/to_html.py`: HTML generation with Tailwind and export.
- `src/export_cursor_chat/main.py`: Typer CLI with commands: `markdown`, `html`, `ui`.
- `app.py`: Streamlit UI for browsing chats.
