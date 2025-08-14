from pathlib import Path
from .cursor_to_md import RawStore, ComposerRow, BubbleRow, parse_bubble_row, parse_composer_row
from .utils import safe_filename, ensure_output_dir


def generate_markdown_for_composer(raw: RawStore, composer_row: ComposerRow) -> tuple[str, str] | None:
    comp = parse_composer_row(composer_row)
    if not comp:
        return None
    bubble_index: dict[tuple[str, str], BubbleRow] = {
        (b.composer_id, b.bubble_id): b for b in raw.bubbles
    }
    title = comp.name or "untitled"
    lines: list[str] = [f"# {title}", ""]
    for h in comp.full_conversation_headers_only:
        role = "User" if h.type == 1 else ("Assistant" if h.type == 2 else "Unknown")
        b_row = bubble_index.get((comp.composer_id, h.bubble_id))
        if not b_row:
            continue
        b = parse_bubble_row(b_row)
        if not b:
            continue
        if b.thinking_text is not None:
            lines += [f"### {role} [thinking]", "", b.thinking_text, ""]
        if b.text is not None:
            lines += [f"### {role} [chat]", "", b.text, ""]
    return title, "\n".join(lines)


def export_markdown(raw: RawStore, output_dir: Path) -> int:
    ensure_output_dir(output_dir)
    used: dict[str, int] = {}
    count = 0
    for c_row in raw.composers:
        built = generate_markdown_for_composer(raw, c_row)
        if not built:
            continue
        title, md = built
        base = safe_filename(title)
        suffix = used.get(base, 0)
        used[base] = suffix + 1
        filename = f"{base}.md" if suffix == 0 else f"{base}_{suffix}.md"
        path = output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            f.write(md)
        count += 1
    return count


