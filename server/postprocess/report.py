"""Report orchestration: detect the run's use case, execute the matching notebook
(engine "notebook"), or build the same sections directly in-process (engine "direct")
when the notebook path is unavailable/fails. Results cached under runs/<id>/report/.
"""
from __future__ import annotations

import json
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import common as C
from . import ev as ev_mod
from . import od as od_mod
from . import admm as admm_mod
from . import swod as swod_mod

SERVER_DIR = Path(__file__).resolve().parent.parent
NOTEBOOKS_DIR = SERVER_DIR.parent / "notebooks"

_LOCK = threading.Lock()

_BUILDERS = {
    "ev": ev_mod.build_sections,
    "od": od_mod.build_sections,
    "admm": admm_mod.build_sections,
    "swod": swod_mod.build_sections,
}
_NOTEBOOKS = {
    "ev": "ev_report.ipynb",
    "od": "od_report.ipynb",
    "admm": "admm_report.ipynb",
    "swod": "swod_report.ipynb",
}
_CONTEXTS = {"ev": ev_mod.context_signature}


def _context_for(usecase: str, run_dir: Path) -> str:
    fn = _CONTEXTS.get(usecase)
    if fn is None:
        return ""
    try:
        return fn(run_dir)
    except Exception:  # noqa: BLE001
        return ""


def _cached_context(meta_path: Path) -> str | None:
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8")).get("context")
    except ValueError:
        return None


class UnsupportedUseCase(Exception):
    pass


class OutputsMissing(Exception):
    pass


@dataclass
class ReportInfo:
    engine: str
    usecase: str
    html_path: Path
    cached: bool = False


def detect_usecase(run_dir: Path) -> str:
    types = C.component_types(C.load_wiring(run_dir))
    if "EVCSComponent" in types:
        return "ev"
    if "ODComponent" in types:
        return "od"
    if "PnnlDopfAdmmComponent" in types:
        return "admm"
    if "PnnlEmtSwodComponent" in types or "SWODComponent" in types:
        return "swod"
    raise UnsupportedUseCase(
        "Post-process reports are available for the ORNL EV, OD, ADMM, and SWOD use cases only."
    )


def _ensure_outputs(run_dir: Path) -> None:
    """Gather recorder feather/csv files found in build/ into outputs/ if not already present."""
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    import shutil
    for ext in ("*.feather", "*.csv"):
        for path in run_dir.rglob(ext):
            if path.parent != outputs_dir:
                dest = outputs_dir / path.name
                if not dest.exists():
                    try:
                        shutil.copy(path, dest)
                    except Exception:
                        pass


def _require_outputs(usecase: str, run_dir: Path) -> None:
    _ensure_outputs(run_dir)
    out = run_dir / "outputs"
    if usecase == "ev":
        needed = ["voltage_real.feather", "voltage_imag.feather", "topology.json"]
    elif usecase == "od":
        needed = ["events.feather"]
    elif usecase == "admm":
        if not (out / "topology.json").exists() and not any(run_dir.rglob("topology.json")):
            raise OutputsMissing("Run outputs not found (topology.json). Wait for the run to finish, then try again.")
        return
    elif usecase == "swod":
        needed = ["swod_oscillation_frequency.feather"]
    else:
        needed = []

    missing = [f for f in needed if not (out / f).exists()]
    if missing:
        raise OutputsMissing(
            f"Run outputs not found ({', '.join(missing)}). "
            "Wait for the run to finish, then try again."
        )


def html_path(run_dir: Path) -> Path:
    return Path(run_dir) / "report" / "report.html"


def _run_notebook(usecase: str, run_dir: Path, report_dir: Path) -> None:
    import nbformat
    from nbclient import NotebookClient
    from nbconvert import HTMLExporter

    src = NOTEBOOKS_DIR / _NOTEBOOKS[usecase]
    nb = nbformat.read(src, as_version=4)
    override = nbformat.v4.new_code_cell(
        source=(
            f"RUN_DIR = r'{Path(run_dir).resolve()}'\n"
            f"SERVER_DIR = r'{SERVER_DIR}'"
        ),
        metadata={"tags": ["injected-parameters"]},
    )
    nb.cells.insert(1, override)
    client = NotebookClient(
        nb,
        timeout=600,
        startup_timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(NOTEBOOKS_DIR)}},
    )
    client.execute()
    nbformat.write(nb, report_dir / "report.ipynb")
    exporter = HTMLExporter()
    exporter.exclude_input = True
    body, _ = exporter.from_notebook_node(nb)
    (report_dir / "report.html").write_text(body, encoding="utf-8")


def _run_direct(usecase: str, run_dir: Path, report_dir: Path) -> None:
    title, sections = _BUILDERS[usecase](run_dir)
    subtitle = ""
    (report_dir / "report.html").write_text(
        C.render_html(title, subtitle, sections), encoding="utf-8"
    )


def generate(run_dir: Path, force: bool = False) -> ReportInfo:
    run_dir = Path(run_dir)
    report_dir = run_dir / "report"
    html = report_dir / "report.html"
    meta_path = report_dir / "meta.json"

    usecase = detect_usecase(run_dir)
    # A cached report is only valid while its comparison context (e.g. which baseline run it paired with) is unchanged — a new baseline invalidates it.
    context = _context_for(usecase, run_dir)

    if html.exists() and not force and _cached_context(meta_path) == context:
        engine = "unknown"
        if meta_path.exists():
            try:
                engine = json.loads(meta_path.read_text(encoding="utf-8")).get("engine", "unknown")
            except ValueError:
                pass
        return ReportInfo(engine=engine, usecase=usecase, html_path=html, cached=True)

    with _LOCK:
        if html.exists() and not force and _cached_context(meta_path) == context:
            return generate(run_dir, force=False)
        _require_outputs(usecase, run_dir)
        report_dir.mkdir(exist_ok=True)

        engine = "notebook"
        notebook_error = None
        try:
            _run_notebook(usecase, run_dir, report_dir)
        except Exception:  # noqa: BLE001 — any notebook failure degrades to direct
            notebook_error = traceback.format_exc(limit=3)
            engine = "direct"
            _run_direct(usecase, run_dir, report_dir)

        meta = {
            "engine": engine,
            "usecase": usecase,
            "context": context,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        if notebook_error:
            meta["notebook_error"] = notebook_error
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ReportInfo(engine=engine, usecase=usecase, html_path=html)
