from pathlib import Path
import os
import typer

from .cursor_to_md import (
    get_default_db_path,
    connect_readonly,
    get_cursor_disk_kv_rows,
    group_rows_by_type,
    dump_rows_to_files,
)
from .to_markdown import export_markdown
from .to_html import export_html

app = typer.Typer(help="Export Cursor chat history to Markdown or HTML, or preview via Streamlit UI.")


@app.callback()
def _version():
    """Export Cursor chat history."""
    return


@app.command("markdown")
def cmd_markdown(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False, readable=True, help="Path to Cursor state.vscdb; defaults to APPDATA Cursor DB"),
    out_dir: Path = typer.Option(Path("chat_output_md"), help="Directory to write Markdown files to"),
    dump_raw: Path | None = typer.Option(None, help="Optional directory to dump raw JSON rows for debugging"),
):
    """Export chats to Markdown files."""
    if db_path is None:
        db_path = get_default_db_path()
    with connect_readonly(db_path) as conn:
        rows = get_cursor_disk_kv_rows(conn)
    raw = group_rows_by_type(rows)
    if dump_raw is not None:
        dump_rows_to_files(rows, dump_raw)
    count = export_markdown(raw, out_dir)
    typer.echo(f"Exported {count} chats to {out_dir}/")


@app.command("html")
def cmd_html(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False, readable=True, help="Path to Cursor state.vscdb; defaults to APPDATA Cursor DB"),
    out_dir: Path = typer.Option(Path("chat_output_html"), help="Directory to write HTML files to"),
    dump_raw: Path | None = typer.Option(None, help="Optional directory to dump raw JSON rows for debugging"),
):
    """Export chats to HTML files with Tailwind CSS styling."""
    if db_path is None:
        db_path = get_default_db_path()
    with connect_readonly(db_path) as conn:
        rows = get_cursor_disk_kv_rows(conn)
    raw = group_rows_by_type(rows)
    if dump_raw is not None:
        dump_rows_to_files(rows, dump_raw)
    count = export_html(raw, out_dir)
    typer.echo(f"Exported {count} chats to {out_dir}/")


@app.command("ui")
def cmd_ui(
    db_path: Path = typer.Option(None, exists=True, dir_okay=False, readable=True, help="Path to Cursor state.vscdb; defaults to APPDATA Cursor DB"),
):
    """Launch the Streamlit UI to browse chats."""
    # Defer import so Typer help remains fast and streamlit is optional dependency
    import subprocess
    import sys
    from pathlib import Path as _Path

    env = dict(**os.environ)
    if db_path is None:
        # Allow app.py to resolve default on its own if not provided
        pass
    else:
        env["CURSOR_CHAT_DB_PATH"] = str(db_path)
    app_path = _Path(__file__).resolve().parent.parent.parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False, env=env)


def main():
    app()


if __name__ == "__main__":
    main()


