from pathlib import Path
from html import escape
from .cursor_to_md import RawStore, ComposerRow, BubbleRow, parse_bubble_row, parse_composer_row
from .utils import safe_filename, ensure_output_dir


TAILWIND_CDN = "https://cdn.jsdelivr.net/npm/tailwindcss@latest/dist/tailwind.min.css"


def _render_conversation_html(raw: RawStore, composer_row: ComposerRow) -> tuple[str, str] | None:
    comp = parse_composer_row(composer_row)
    if not comp:
        return None
    bubble_index: dict[tuple[str, str], BubbleRow] = {
        (b.composer_id, b.bubble_id): b for b in raw.bubbles
    }
    title = comp.name or "untitled"
    items: list[str] = []
    for h in comp.full_conversation_headers_only:
        role = "User" if h.type == 1 else ("Assistant" if h.type == 2 else "Unknown")
        role_color = "bg-blue-50 border-blue-200" if role == "User" else ("bg-green-50 border-green-200" if role == "Assistant" else "bg-gray-50 border-gray-200")
        b_row = bubble_index.get((comp.composer_id, h.bubble_id))
        if not b_row:
            continue
        b = parse_bubble_row(b_row)
        if not b:
            continue
        if b.thinking_text is not None:
            items.append(
                f"<div class='p-4 my-3 border rounded {role_color}'><div class='text-xs text-gray-500 mb-1'>{escape(role)} [thinking]</div><pre class='whitespace-pre-wrap text-gray-700'>{escape(b.thinking_text)}</pre></div>"
            )
        if b.text is not None:
            items.append(
                f"<div class='p-4 my-3 border rounded {role_color}'><div class='text-xs text-gray-500 mb-1'>{escape(role)} [chat]</div><div class='prose max-w-none'>{escape(b.text)}</div></div>"
            )
    html_body = "".join(items)
    html_page = f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <link href=\"{TAILWIND_CDN}\" rel=\"stylesheet\" />
  <style>
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, Noto Sans, Ubuntu, Cantarell, Helvetica Neue, sans-serif; }}
    .prose {{ white-space: pre-wrap; }}
  </style>
  </head>
<body class=\"bg-gray-100\">
  <main class=\"max-w-3xl mx-auto py-8 px-4\">
    <h1 class=\"text-3xl font-bold mb-6\">{escape(title)}</h1>
    {html_body}
  </main>
</body>
</html>
"""
    return title, html_page


def export_html(raw: RawStore, output_dir: Path) -> int:
    ensure_output_dir(output_dir)
    used: dict[str, int] = {}
    count = 0
    for c_row in raw.composers:
        built = _render_conversation_html(raw, c_row)
        if not built:
            continue
        title, doc = built
        base = safe_filename(title)
        suffix = used.get(base, 0)
        used[base] = suffix + 1
        filename = f"{base}.html" if suffix == 0 else f"{base}_{suffix}.html"
        path = output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            f.write(doc)
        count += 1
    return count


