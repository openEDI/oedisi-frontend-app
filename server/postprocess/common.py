"""Shared helpers for per-use-case post-process reports.

Figures are matplotlib (Agg); reports render to a single self-contained HTML with
figures embedded as base64 PNGs. The same section builders feed both the notebook
path (inline display) and the direct-HTML fallback path.
"""
from __future__ import annotations

import base64
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

NAVY = "#1A204C"
BLUE = "#21409A"
MBLUE = "#085A9B"
GREEN = "#1D772A"
ORANGE = "#FAA449"
RED = "#C00000"
GRAY = "#6B7486"
LIGHT = "#D9DFEA"
PANEL = "#EFF1F6"


def load_wiring(run_dir: Path) -> dict[str, Any]:
    path = Path(run_dir) / "wiring.json"
    if not path.exists():
        raise FileNotFoundError(f"wiring.json not found in {run_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def component_types(wiring: dict[str, Any]) -> set[str]:
    return {c.get("type") for c in wiring.get("components", [])}


def component_params(wiring: dict[str, Any], ctype: str) -> dict[str, Any]:
    for c in wiring.get("components", []):
        if c.get("type") == ctype:
            return c.get("parameters") or {}
    return {}


def fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor="white", bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def table_html(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows
    )
    return (
        '<div class="scroll"><table><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></div>"
    )


def stat_band(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div class="stat"><div class="k">{k}</div><div class="v">{v}</div></div>'
        for k, v in items
    )
    return f'<div class="stats">{cells}</div>'


_CSS = """
body{font-family:Arial,Segoe UI,sans-serif;margin:0;background:#F4F5F8;color:#1A204C}
.wrap{max-width:1040px;margin:0 auto;padding:22px 22px 60px}
h1{font-size:24px;margin:6px 0 2px}
.meta{color:#6B7486;font-size:13px;margin-bottom:16px}
section{background:#fff;border:1px solid #DDE3EC;border-radius:9px;padding:16px 20px;margin-top:16px}
h2{font-size:17px;color:#21409A;margin:0 0 10px}
img{max-width:100%;height:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid #DDE3EC;padding:6px 9px;text-align:left}
th{background:#EFF1F6;color:#21409A}
tbody tr:nth-child(even){background:#FAFBFD}
.scroll{overflow-x:auto}
.stats{display:flex;flex-wrap:wrap;gap:12px}
.stat{background:#EFF1F6;border:1px solid #DDE3EC;border-radius:8px;padding:9px 14px;min-width:130px}
.stat .k{font-size:11px;color:#6B7486;text-transform:uppercase;letter-spacing:.04em}
.stat .v{font-size:17px;font-weight:700;margin-top:2px}
.note{color:#6B7486;font-size:12.5px;font-style:italic;margin-top:10px}
"""


def render_html(title: str, subtitle: str, sections: list[tuple[str, str]]) -> str:
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{title}</title><style>{_CSS}</style></head><body><div class='wrap'>",
        f"<h1>{title}</h1><div class='meta'>{subtitle} · generated "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>",
    ]
    for heading, inner in sections:
        parts.append(f"<section><h2>{heading}</h2>{inner}</section>")
    parts.append("</div></body></html>")
    return "".join(parts)


def img_html(fig) -> str:
    return f'<img src="data:image/png;base64,{fig_to_b64(fig)}"/>'


def display_sections(sections: list[tuple[str, str]]) -> None:
    """Notebook path: render the same sections inline."""
    from IPython.display import HTML, display

    display(HTML(f"<style>{_CSS}</style>"))
    for heading, inner in sections:
        display(HTML(f"<section><h2 style='color:#21409A'>{heading}</h2>{inner}</section>"))
