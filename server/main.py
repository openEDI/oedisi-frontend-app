"""FastAPI server for the OEDISI frontend app.

Replaces the legacy Express server (`index.js` + `database.js`). Two endpoint
groups:

* `/api/templates` — file-based template CRUD (parity with the JS server).
* `/api/runs` — build an oedisi runner config in-process and launch a HELICS
  simulation subprocess.

See `CLAUDE.md` in this folder for the design rationale.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import psutil
import pyarrow.feather as pa_feather
import pyarrow.types as pa_types
import uvicorn
from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from oedisi.componentframework.basic_component import (
    ComponentDescription,
    basic_component,
)
from oedisi.componentframework.system_configuration import (
    WiringDiagram,
    generate_runner_config,
)
from pydantic import ConfigDict


class AppWiringDiagram(WiringDiagram):
    """WiringDiagram + whatever frontend extras.

    The frontend also sends `description`, `createdAt`, and potentially more.
    `model_config` allows extras.

    Component-level extras (e.g. helics_config_override) will only
    be saved if the version of oedisi has it (see main vs released).
    """

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SERVER_DIR = Path(__file__).resolve().parent
DATA_DIR = SERVER_DIR.parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
RUNS_DIR = SERVER_DIR / "runs"
COMPONENTS_JSON_PATH = SERVER_DIR / "components.json"

TEMPLATE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Accept any sane directory-name shape. Most runs are UUID hex,
# but we accept potential new ones.
RunId = Annotated[str, PathParam(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------


def _check_components_env() -> None:
    """Fail fast if components.json references ${OEDISI_COMPONENTS} but it's unset.

    Run from the lifespan hook so uvicorn aborts boot with a clear error
    instead of waiting for the first POST /api/runs.
    """
    raw = COMPONENTS_JSON_PATH.read_text(encoding="utf-8")

    if "${OEDISI_COMPONENTS}" in raw and not os.environ.get("OEDISI_COMPONENTS"):
        raise RuntimeError(
            "OEDISI_COMPONENTS environment variable is not set, but "
            f"{COMPONENTS_JSON_PATH.name} references ${{OEDISI_COMPONENTS}}.\n"
            "Set it to the path of your local oedisi Components directory"
            "e.g.:\n"
            '    export OEDISI_COMPONENTS="$HOME/Programming/oedisi-components/Components"\n'
            "(add it to your shell rc to make it permanent)."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _check_components_env()
    except RuntimeError as exc:
        # uvicorn swallows the traceback by default; print plainly so the
        # error is the first thing the user sees in `npm run dev:server`.
        print(f"\n[startup error] {exc}\n", file=sys.stderr)
        raise
    _restore_runs()
    yield


# ---------------------------------------------------------------------------
# App / CORS
# ---------------------------------------------------------------------------

app = FastAPI(title="oedisi-frontend server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Template storage
# ---------------------------------------------------------------------------


def _validate_template_id(template_id: str) -> None:
    if not template_id or not TEMPLATE_ID_PATTERN.match(template_id):
        raise HTTPException(status_code=400, detail="Invalid template id format")


def _template_path(template_id: str) -> Path:
    _validate_template_id(template_id)
    return TEMPLATES_DIR / f"{template_id}.json"


def _validate_template_payload(template: dict[str, Any]) -> None:
    required_str = ("id", "name", "description", "createdAt")
    for key in required_str:
        if not isinstance(template.get(key), str):
            raise HTTPException(status_code=400, detail=f"Template {key} is required")
    if not isinstance(template.get("nodes"), list):
        raise HTTPException(status_code=400, detail="Template nodes must be an array")
    if not isinstance(template.get("edges"), list):
        raise HTTPException(status_code=400, detail="Template edges must be an array")
    _validate_template_id(template["id"])


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _read_template(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/templates")
def list_templates() -> list[dict[str, Any]]:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    templates: list[dict[str, Any]] = []
    for path in TEMPLATES_DIR.glob("*.json"):
        try:
            templates.append(_read_template(path))
        except json.JSONDecodeError:
            # Skip corrupt files; the JS server logged-and-skipped too.
            continue
    templates.sort(key=lambda t: t.get("createdAt", ""), reverse=True)
    return templates


@app.get("/api/templates/{template_id}")
def get_template(template_id: str) -> dict[str, Any]:
    path = _template_path(template_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return _read_template(path)


@app.post("/api/templates")
def create_template(template: dict[str, Any]) -> dict[str, Any]:
    if not template.get("id"):
        # Match the JS server: millisecond timestamp string.
        template["id"] = str(int(__import__("time").time() * 1000))
    if not template.get("createdAt"):
        template["createdAt"] = _iso(datetime.now(timezone.utc))

    _validate_template_payload(template)
    _atomic_write_json(_template_path(template["id"]), template)
    return {
        "success": True,
        "id": template["id"],
        "message": "Template saved successfully",
    }


@app.put("/api/templates/{template_id}")
def update_template(template_id: str, template: dict[str, Any]) -> dict[str, Any]:
    template["id"] = template_id

    path = _template_path(template_id)
    if path.exists():
        existing = _read_template(path)
        if existing.get("createdAt"):
            template["createdAt"] = existing["createdAt"]

    _validate_template_payload(template)
    _atomic_write_json(path, template)
    return {"success": True, "message": "Template updated successfully"}


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str) -> dict[str, Any]:
    path = _template_path(template_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    path.unlink()
    return {"success": True, "message": "Template deleted successfully"}


# ---------------------------------------------------------------------------
# oedisi build (in-process)
# ---------------------------------------------------------------------------


def _bad_type_checker(_type: Any, _x: Any) -> bool:  # noqa: ANN401
    return True


def _resolve_component_path(raw: str) -> str:
    """Expand ${OEDISI_COMPONENTS} and ~ in a components.json entry.

    Raises a clear error if `OEDISI_COMPONENTS` is referenced but unset, so
    the failure mode is obvious to anyone setting up the project for the
    first time.
    """
    if "${OEDISI_COMPONENTS}" in raw:
        components_root = os.environ.get("OEDISI_COMPONENTS")
        if not components_root:
            raise RuntimeError(
                "OEDISI_COMPONENTS environment variable is not set. "
                "Set it to the path of your local oedisi-example Components "
                "directory (e.g. ~/Programming/oedisi-example/Components)."
            )
        raw = raw.replace("${OEDISI_COMPONENTS}", components_root)
    return os.path.expanduser(raw)


def load_component_types() -> dict[str, Any]:
    """Load the component-name → BasicComponent mapping from components.json."""
    with open(COMPONENTS_JSON_PATH) as f:
        mapping = json.load(f)

    types: dict[str, Any] = {}
    for name, component_def_path in mapping.items():
        path = _resolve_component_path(component_def_path)
        with open(path) as f:
            comp_desc = ComponentDescription.model_validate(json.load(f))
        comp_desc.directory = os.path.dirname(path)
        types[name] = basic_component(comp_desc, _bad_type_checker)
    return types


def build_runner(wiring_diagram: WiringDiagram, build_dir: Path) -> None:
    component_types = load_component_types()
    runner_config = generate_runner_config(
        wiring_diagram, component_types, target_directory=str(build_dir)
    )
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "system_runner.json").write_text(
        runner_config.model_dump_json(indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Run tracking
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    pid: int
    started_at: datetime
    template_id: str | None
    run_dir: Path
    name: str
    status: str  # "running" | "done" | "failed" | "unknown"
    exit_code: int | None = None
    ended_at: datetime | None = None


runs: dict[str, RunRecord] = {}

# Hold strong refs to watcher tasks — asyncio's create_task docs warn the
# task can be GC'd mid-run otherwise. Tasks drop themselves via done_callback.
_watcher_tasks: set[asyncio.Task[None]] = set()


def _run_json_path(run_dir: Path) -> Path:
    return run_dir / "run.json"


def _write_run_start(run_dir: Path, record: RunRecord) -> None:
    _atomic_write_json(
        _run_json_path(run_dir),
        {
            "pid": record.pid,
            "started_at": _iso(record.started_at),
            "template_id": record.template_id,
            "name": record.name,
        },
    )


def _write_run_finish(record: RunRecord) -> None:
    try:
        data = json.loads(
            _run_json_path(record.run_dir).read_text(encoding="utf-8")
        )
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data["exit_code"] = record.exit_code
    data["ended_at"] = _iso(record.ended_at) if record.ended_at else None
    _atomic_write_json(_run_json_path(record.run_dir), data)


async def _watch_proc(
    run_id: str, proc: asyncio.subprocess.Process
) -> None:
    """Await process exit, update the RunRecord, and persist completion.

    Sole writer of `exit_code`/`ended_at`/terminal `status` on the record —
    `_serialize_run` only reads, so no synchronization is needed. If the
    server exits before this resumes, the subprocess keeps going on its own;
    we just don't record the outcome, and the boot scan marks it "unknown".
    """
    code = await proc.wait()
    record = runs.get(run_id)
    if record is None:
        return  # run was deleted while we waited
    record.exit_code = code
    record.ended_at = datetime.now(timezone.utc)
    record.status = "done" if code == 0 else "failed"
    try:
        _write_run_finish(record)
    except OSError as exc:
        print(f"[run {run_id}] failed to write run.json: {exc}", file=sys.stderr)


def _tree_kill(pid: int) -> None:
    """Kill the process and all its descendants.

    `helics run` spawns a broker plus one federate per component; signalling
    only the parent orphans the broker, which then lingers holding its port.
    """
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    for child in parent.children(recursive=True):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def _restore_runs() -> None:
    """Rebuild `runs` from `runs/*/run.json` on startup.

    We deliberately do not try to reattach to live PIDs: Windows aggressively
    reuses PIDs, and validating identity via create_time is more complexity
    than this tool needs. Runs without a recorded `exit_code` become
    "unknown" — the subprocess may or may not have finished; check the logs.
    """
    if not RUNS_DIR.exists():
        return
    for run_dir in RUNS_DIR.iterdir():
        if not run_dir.is_dir():
            continue
        path = _run_json_path(run_dir)
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        pid = data.get("pid")
        started_at_raw = data.get("started_at")
        if not isinstance(pid, int) or not isinstance(started_at_raw, str):
            continue
        exit_code = data.get("exit_code")
        ended_at_raw = data.get("ended_at")
        try:
            started_at = datetime.fromisoformat(started_at_raw)
            ended_at = (
                datetime.fromisoformat(ended_at_raw)
                if isinstance(ended_at_raw, str)
                else None
            )
        except ValueError:
            # Malformed timestamp (hand-edited or truncated file). Skip — a
            # single bad run.json must not take down boot for everyone else.
            continue
        if exit_code is not None:
            status = "done" if exit_code == 0 else "failed"
        else:
            status = "unknown"
        runs[run_dir.name] = RunRecord(
            pid=pid,
            started_at=started_at,
            template_id=data.get("template_id"),
            run_dir=run_dir,
            name=data.get("name", ""),
            status=status,
            exit_code=exit_code,
            ended_at=ended_at,
        )


@app.post("/api/runs")
async def start_run(
    wiring_diagram: AppWiringDiagram,
    template_id: str | None = None,
) -> dict[str, str]:
    run_id = uuid.uuid4().hex
    run_dir = RUNS_DIR / run_id
    build_dir = run_dir / "build"

    try:
        build_runner(wiring_diagram, build_dir)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Build failed: {exc}") from exc

    # Snapshot what was submitted — authoritative record of what actually ran,
    # independent of whether the originating template is later edited or deleted.
    (run_dir / "wiring.json").write_text(
        wiring_diagram.model_dump_json(indent=2), encoding="utf-8"
    )

    proc = await asyncio.create_subprocess_exec(
        "helics",
        "run",
        f"--path={build_dir / 'system_runner.json'}",
        cwd=build_dir,
    )
    record = RunRecord(
        pid=proc.pid,
        started_at=datetime.now(timezone.utc),
        template_id=template_id,
        run_dir=run_dir,
        name=wiring_diagram.name,
        status="running",
    )
    runs[run_id] = record
    _write_run_start(run_dir, record)
    task = asyncio.create_task(_watch_proc(run_id, proc))
    _watcher_tasks.add(task)
    task.add_done_callback(_watcher_tasks.discard)
    return {"run_id": run_id}


def _serialize_run(run_id: str, record: RunRecord) -> dict[str, Any]:
    out: dict[str, Any] = {
        "run_id": run_id,
        "name": record.name,
        "started_at": _iso(record.started_at),
        "template_id": record.template_id,
        "run_dir": str(record.run_dir),
        "status": record.status,
    }
    if record.exit_code is not None:
        out["exit_code"] = record.exit_code
    if record.ended_at is not None:
        out["ended_at"] = _iso(record.ended_at)
    return out


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return sorted(
        (_serialize_run(rid, rec) for rid, rec in runs.items()),
        key=lambda r: r["started_at"],
        reverse=True,
    )


@app.get("/api/runs/{run_id}")
def run_status(run_id: RunId) -> dict[str, Any]:
    record = runs.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run_id, record)


@app.get("/api/runs/{run_id}/wiring")
def run_wiring(run_id: RunId) -> FileResponse:
    """Ship the snapshotted wiring.json straight from disk.

    Read from disk rather than `runs[run_id]` so this works for restored runs
    where we never held the diagram in memory.
    """
    wiring_path = RUNS_DIR / run_id / "wiring.json"
    if not wiring_path.exists():
        raise HTTPException(status_code=404, detail="Wiring not found")
    return FileResponse(wiring_path, media_type="application/json")


@app.get("/api/runs/{run_id}/logs/{component}")
def run_log(run_id: RunId, component: str) -> FileResponse:
    # Guard against path traversal — component name is a filename segment only.
    if "/" in component or "\\" in component or ".." in component:
        raise HTTPException(status_code=400, detail="Invalid component name")

    log_path = RUNS_DIR / run_id / "build" / f"{component}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return FileResponse(log_path, media_type="text/plain; charset=utf-8")


def _load_run_wiring(run_id: str) -> dict[str, Any]:
    wiring_path = RUNS_DIR / run_id / "wiring.json"
    if not wiring_path.exists():
        raise HTTPException(status_code=404, detail="Run wiring not found")
    return json.loads(wiring_path.read_text())


def _recorder_feather_path(run_id: str, component: dict[str, Any]) -> Path | None:
    """Path to the feather a Recorder writes, or None if it's not on disk yet."""
    name = component.get("name")
    params = component.get("parameters") or {}
    feather_name = params.get("feather_filename")
    if not name or not feather_name:
        return None
    path = RUNS_DIR / run_id / "build" / name / feather_name
    return path if path.exists() else None


def _infer_field(name: str, arrow_type: Any) -> dict[str, str]:
    """Map an Arrow column to a graphic-walker IMutField."""
    if name == "time" or pa_types.is_temporal(arrow_type):
        semantic, analytic = "temporal", "dimension"
    elif pa_types.is_integer(arrow_type) or pa_types.is_floating(arrow_type):
        semantic, analytic = "quantitative", "measure"
    else:
        semantic, analytic = "nominal", "dimension"
    return {
        "fid": name,
        "name": name,
        "semanticType": semantic,
        "analyticType": analytic,
    }


@app.get("/api/runs/{run_id}/results")
def list_results(run_id: RunId) -> list[dict[str, Any]]:
    """Manifest of datasets available for a run. v1: Recorder outputs only."""
    wiring = _load_run_wiring(run_id)
    entries: list[dict[str, Any]] = []
    for component in wiring.get("components", []):
        if component.get("type") != "Recorder":
            continue
        path = _recorder_feather_path(run_id, component)
        if path is None:
            continue
        entries.append({
            "id": component["name"],
            "label": component["name"],
            "type": "Recorder",
            "size_bytes": path.stat().st_size,
        })
    return entries


@app.get("/api/runs/{run_id}/results/{dataset_id}")
def get_result(run_id: RunId, dataset_id: str) -> dict[str, Any]:
    if "/" in dataset_id or "\\" in dataset_id or ".." in dataset_id:
        raise HTTPException(status_code=400, detail="Invalid dataset id")
    wiring = _load_run_wiring(run_id)
    component = next(
        (c for c in wiring.get("components", [])
         if c.get("type") == "Recorder" and c.get("name") == dataset_id),
        None,
    )
    if component is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    path = _recorder_feather_path(run_id, component)
    if path is None:
        raise HTTPException(status_code=404, detail="Dataset file missing")

    table = pa_feather.read_table(path)
    fields = [_infer_field(f.name, f.type) for f in table.schema]
    data = table.to_pylist()
    return {"fields": fields, "data": data}


@app.delete("/api/runs/{run_id}")
def kill_run(run_id: RunId) -> dict[str, bool]:
    record = runs.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    # Only kill runs we launched in this process. "unknown" runs have a pid
    # from a previous boot; the OS may have reassigned it.
    if record.status == "running":
        _tree_kill(record.pid)
    return {"success": True}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    uvicorn.run("main:app", host="127.0.0.1", port=3001, reload=True)


if __name__ == "__main__":
    main()
