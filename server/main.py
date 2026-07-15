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
import logging
import os
import re
import shutil
import socket
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import psutil
import pyarrow.feather as pa_feather
import uvicorn
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Path as PathParam,
)
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

from output_annotations import OutputsList, annotate_outputs


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
# Per-user identity
# ---------------------------------------------------------------------------
#
# Single-user by default: every request resolves to DEFAULT_USER, so a local
# `npm run dev:server` (and CI) needs no auth setup. Set OEDISI_MULTI_USER to
# opt into per-user mode, where nginx authenticates via HTTP Basic and injects
# the username as the `X-Remote-User` header (see deploy/nginx.conf). The
# backend trusts that header *because* it only listens on localhost — nginx is
# the only caller. Every request's data is namespaced under the resolved user,
# so a username that could escape its directory (`..`, `/`) must never reach
# the filesystem.

DEFAULT_USER = "dev"

# Same shape as a template id: directory-safe, no traversal characters.
USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def current_user(
    x_remote_user: Annotated[str | None, Header()] = None,
) -> str:
    """Resolve the user for this request.

    Single-user mode (default): always DEFAULT_USER; the header is ignored.

    Multi-user mode (OEDISI_MULTI_USER set): resolve from the nginx-injected
    header and fail closed on a missing/invalid identity, which forces nginx to
    always sit in front of the backend in production.
    """
    if not os.environ.get("OEDISI_MULTI_USER"):
        return DEFAULT_USER
    if x_remote_user is None:
        raise HTTPException(status_code=401)
    if not USER_ID_PATTERN.match(x_remote_user):
        raise HTTPException(status_code=400, detail="Invalid user")
    return x_remote_user


CurrentUser = Annotated[str, Depends(current_user)]


def _user_templates_dir(user: str) -> Path:
    return TEMPLATES_DIR / user


def _user_runs_dir(user: str) -> Path:
    return RUNS_DIR / user


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


def _template_path(user: str, template_id: str) -> Path:
    _validate_template_id(template_id)
    return _user_templates_dir(user) / f"{template_id}.json"


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
def list_templates(user: CurrentUser) -> list[dict[str, Any]]:
    user_dir = _user_templates_dir(user)
    user_dir.mkdir(parents=True, exist_ok=True)
    templates: list[dict[str, Any]] = []
    for path in user_dir.glob("*.json"):
        try:
            templates.append(_read_template(path))
        except json.JSONDecodeError:
            # Skip corrupt files; the JS server logged-and-skipped too.
            continue
    templates.sort(key=lambda t: t.get("createdAt", ""), reverse=True)
    return templates


@app.get("/api/templates/{template_id}")
def get_template(template_id: str, user: CurrentUser) -> dict[str, Any]:
    path = _template_path(user, template_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return _read_template(path)


@app.post("/api/templates")
def create_template(template: dict[str, Any], user: CurrentUser) -> dict[str, Any]:
    if not template.get("id"):
        # Match the JS server: millisecond timestamp string.
        template["id"] = str(int(__import__("time").time() * 1000))
    if not template.get("createdAt"):
        template["createdAt"] = _iso(datetime.now(timezone.utc))

    _validate_template_payload(template)
    _atomic_write_json(_template_path(user, template["id"]), template)
    return {
        "success": True,
        "id": template["id"],
        "message": "Template saved successfully",
    }


@app.put("/api/templates/{template_id}")
def update_template(
    template_id: str, template: dict[str, Any], user: CurrentUser
) -> dict[str, Any]:
    template["id"] = template_id

    path = _template_path(user, template_id)
    if path.exists():
        existing = _read_template(path)
        if existing.get("createdAt"):
            template["createdAt"] = existing["createdAt"]

    _validate_template_payload(template)
    _atomic_write_json(path, template)
    return {"success": True, "message": "Template updated successfully"}


@app.delete("/api/templates/{template_id}")
def delete_template(template_id: str, user: CurrentUser) -> dict[str, Any]:
    path = _template_path(user, template_id)
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


def load_component_descriptions() -> dict[str, ComponentDescription]:
    """Load the component-name → ComponentDescription mapping from components.json."""
    with open(COMPONENTS_JSON_PATH) as f:
        mapping = json.load(f)

    descriptions: dict[str, ComponentDescription] = {}
    for name, component_def_path in mapping.items():
        path = _resolve_component_path(component_def_path)
        with open(path) as f:
            comp_desc = ComponentDescription.model_validate(json.load(f))
        comp_desc.directory = os.path.dirname(path)
        descriptions[name] = comp_desc
    return descriptions


def build_runner(wiring_diagram: WiringDiagram, build_dir: Path) -> None:
    descriptions = load_component_descriptions()
    component_types = {
        name: basic_component(desc, _bad_type_checker)
        for name, desc in descriptions.items()
    }
    runner_config = generate_runner_config(
        wiring_diagram, component_types, target_directory=str(build_dir)
    )
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "system_runner.json").write_text(
        runner_config.model_dump_json(indent=2), encoding="utf-8"
    )
    (build_dir / "outputs_list.json").write_text(
        annotate_outputs(wiring_diagram, descriptions).model_dump_json(
            indent=2, exclude_none=True
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Run tracking
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    pid: int
    user: str
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
        data = json.loads(_run_json_path(record.run_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data["exit_code"] = record.exit_code
    data["ended_at"] = _iso(record.ended_at) if record.ended_at else None
    _atomic_write_json(_run_json_path(record.run_dir), data)


async def _watch_proc(run_id: str, proc: asyncio.subprocess.Process) -> None:
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
    # Each run.json now sits at runs/<user>/<run_id>/run.json.
    for path in RUNS_DIR.glob("*/*/run.json"):
        run_dir = path.parent
        user = run_dir.parent.name
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
            user=user,
            started_at=started_at,
            template_id=data.get("template_id"),
            run_dir=run_dir,
            name=data.get("name", ""),
            status=status,
            exit_code=exit_code,
            ended_at=ended_at,
        )


# oedisi/HELICS can only host one simulation at a time: the ZMQ broker binds a
# fixed pair of ports, so a second concurrent `helics run` collides on them.
# Default ZMQ broker port (23404) plus its reply channel (23405).
HELICS_BROKER_PORTS: tuple[int, ...] = (23404, 23405)


def _port_in_use(port: int) -> bool:
    """True if something is listening on 127.0.0.1:port.

    Uses a TCP connect rather than psutil.net_connections() — the latter raises
    AccessDenied without root on macOS. connect_ex returns 0 when the connection
    succeeds, i.e. a broker is already bound here.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.05)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _assert_no_run_in_progress() -> None:
    """Reject the request (409) if a simulation is already running.

    Two layers: the in-process check catches a rapid double-submit before the
    broker has bound its port; the port check catches brokers started outside
    this server or left alive (`"unknown"`) across a restart.
    """
    for run_id, record in runs.items():
        if record.status == "running":
            raise HTTPException(
                status_code=409,
                detail=f"A simulation is already running ({record.name or run_id}).",
            )
    busy = [p for p in HELICS_BROKER_PORTS if _port_in_use(p)]
    if busy:
        ports = ", ".join(str(p) for p in busy)
        raise HTTPException(
            status_code=409,
            detail=f"HELICS broker port {ports} in use; a simulation is already running.",
        )


@app.post("/api/runs")
async def start_run(
    wiring_diagram: AppWiringDiagram,
    user: CurrentUser,
    template_id: str | None = None,
) -> dict[str, str]:
    _assert_no_run_in_progress()

    run_id = uuid.uuid4().hex
    run_dir = _user_runs_dir(user) / run_id
    build_dir = run_dir / "build"

    try:
        build_runner(wiring_diagram, build_dir)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Build failed: {exc}") from exc

    (run_dir / "outputs").mkdir(exist_ok=True)

    # Snapshot what was submitted — authoritative record of what actually ran,
    # independent of whether the originating template is later edited or deleted.
    (run_dir / "wiring.json").write_text(
        wiring_diagram.model_dump_json(indent=2), encoding="utf-8"
    )

    # Reserve the slot *before* awaiting the subprocess spawn. The await is the
    # first yield point in this handler, so a concurrent start_run could
    # otherwise slip past _assert_no_run_in_progress() here — no record exists
    # yet and the broker hasn't bound its port. pid is filled in once we have it.
    record = RunRecord(
        pid=-1,
        user=user,
        started_at=datetime.now(timezone.utc),
        template_id=template_id,
        run_dir=run_dir,
        name=wiring_diagram.name,
        status="running",
    )
    runs[run_id] = record

    try:
        proc = await asyncio.create_subprocess_exec(
            "helics",
            "run",
            f"--path={build_dir / 'system_runner.json'}",
            cwd=build_dir,
        )
    except Exception as exc:  # noqa: BLE001
        del runs[run_id]  # release the slot — nothing is running
        raise HTTPException(
            status_code=500, detail=f"Failed to launch helics: {exc}"
        ) from exc

    record.pid = proc.pid
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
def list_runs(user: CurrentUser) -> list[dict[str, Any]]:
    return sorted(
        (_serialize_run(rid, rec) for rid, rec in runs.items() if rec.user == user),
        key=lambda r: r["started_at"],
        reverse=True,
    )


def _get_owned_run(run_id: str, user: str) -> RunRecord:
    """Fetch a run only if it belongs to `user`, else 404.

    The `runs` dict is keyed by globally-unique run_id, so it holds every
    user's runs. 404 rather than 403 keeps another user's run ids unguessable.
    """
    record = runs.get(run_id)
    if record is None or record.user != user:
        raise HTTPException(status_code=404, detail="Run not found")
    return record


@app.get("/api/runs/{run_id}")
def run_status(run_id: RunId, user: CurrentUser) -> dict[str, Any]:
    record = _get_owned_run(run_id, user)
    return _serialize_run(run_id, record)


@app.get("/api/runs/{run_id}/wiring")
def run_wiring(run_id: RunId, user: CurrentUser) -> FileResponse:
    """Ship the snapshotted wiring.json straight from disk.

    Read from disk rather than `runs[run_id]` so this works for restored runs
    where we never held the diagram in memory.
    """
    wiring_path = _user_runs_dir(user) / run_id / "wiring.json"
    if not wiring_path.exists():
        raise HTTPException(status_code=404, detail="Wiring not found")
    return FileResponse(wiring_path, media_type="application/json")


@app.get("/api/runs/{run_id}/download")
def download_run(
    run_id: RunId, user: CurrentUser, background_tasks: BackgroundTasks
) -> FileResponse:
    """Zip the run directory so a remote user can download its outputs."""
    run_dir = _user_runs_dir(user) / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    tmp_dir = Path(tempfile.mkdtemp())
    # base_dir=run_id nests the contents under a run_id/ folder in the zip.
    archive_base = tmp_dir / run_id
    shutil.make_archive(
        str(archive_base), "zip", root_dir=run_dir.parent, base_dir=run_id
    )

    background_tasks.add_task(shutil.rmtree, tmp_dir)
    return FileResponse(
        archive_base.with_suffix(".zip"),
        media_type="application/zip",
        filename=f"{run_id}.zip",
    )


@app.get("/api/runs/{run_id}/logs/{component}")
def run_log(run_id: RunId, component: str, user: CurrentUser) -> FileResponse:
    # Guard against path traversal — component name is a filename segment only.
    if "/" in component or "\\" in component or ".." in component:
        raise HTTPException(status_code=400, detail="Invalid component name")

    log_path = _user_runs_dir(user) / run_id / "build" / f"{component}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return FileResponse(log_path, media_type="text/plain; charset=utf-8")


def _load_run_wiring(user: str, run_id: str) -> dict[str, Any]:
    wiring_path = _user_runs_dir(user) / run_id / "wiring.json"
    if not wiring_path.exists():
        raise HTTPException(status_code=404, detail="Run wiring not found")
    return json.loads(wiring_path.read_text())


def _load_run_outputs(user: str, run_id: str) -> OutputsList:
    """Read the build's outputs_list.json; compute on the fly for older runs."""
    path = _user_runs_dir(user) / run_id / "build" / "outputs_list.json"
    if path.exists():
        return OutputsList.model_validate_json(path.read_text())
    try:
        wiring = WiringDiagram.model_validate(_load_run_wiring(user, run_id))
        return annotate_outputs(wiring, load_component_descriptions())
    except Exception:  # noqa: BLE001 — annotations are optional; never break listing
        logging.exception("Could not backfill output annotations for run %s", run_id)
        return OutputsList()


def _recorder_feather_path(
    user: str, run_id: str, component: dict[str, Any]
) -> Path | None:
    """Path to the feather a Recorder writes, or None if it's not on disk yet."""
    name = component.get("name")
    params = component.get("parameters") or {}
    feather_name = params.get("feather_filename")
    if not name or not feather_name:
        return None
    path = _user_runs_dir(user) / run_id / "build" / name / feather_name
    return path if path.exists() else None


@app.get("/api/runs/{run_id}/results")
def list_results(run_id: RunId, user: CurrentUser) -> list[dict[str, Any]]:
    """Manifest of datasets available for a run. v1: Recorder outputs only."""
    wiring = _load_run_wiring(user, run_id)
    outputs = _load_run_outputs(user, run_id)
    entries: list[dict[str, Any]] = []
    for component in wiring.get("components", []):
        if component.get("type") != "Recorder":
            continue
        path = _recorder_feather_path(user, run_id, component)
        if path is None:
            continue
        annotations = outputs.components.get(component["name"], {})
        feather_name = (component.get("parameters") or {}).get("feather_filename")
        annotation = annotations.get(feather_name)
        entry = {
            "id": component["name"],
            "label": component["name"],
            "type": "Recorder",
            "size_bytes": path.stat().st_size,
        }
        if annotation is not None and annotation.type is not None:
            entry["quantity"] = annotation.model_dump(exclude_none=True)
        entries.append(entry)
    return entries


def _read_result_table(user: str, run_id: str, dataset_id: str):
    """Load a Recorder dataset's feather table, or raise 400/404."""
    if "/" in dataset_id or "\\" in dataset_id or ".." in dataset_id:
        raise HTTPException(status_code=400, detail="Invalid dataset id")
    wiring = _load_run_wiring(user, run_id)
    component = next(
        (
            c
            for c in wiring.get("components", [])
            if c.get("type") == "Recorder" and c.get("name") == dataset_id
        ),
        None,
    )
    if component is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    path = _recorder_feather_path(user, run_id, component)
    if path is None:
        raise HTTPException(status_code=404, detail="Dataset file missing")
    return pa_feather.read_table(path)


@app.get("/api/runs/{run_id}/results/{dataset_id}")
def get_result(run_id: RunId, dataset_id: str, user: CurrentUser) -> dict[str, Any]:
    table = _read_result_table(user, run_id, dataset_id)
    columns = [name for name in table.column_names if name != "time"]
    return {"columns": columns, "data": table.to_pylist()}


def _rows_by_time(table) -> dict[Any, dict[str, Any]]:
    """Index rows by time, insertion-ordered; duplicate times keep the last row."""
    return {row["time"]: row for row in table.to_pylist() if "time" in row}


@app.get("/api/runs/{run_id}/metrics")
def get_metrics(
    run_id: RunId, primary: str, comparison: str, user: CurrentUser
) -> dict[str, Any]:
    """Per-timestep mean absolute relative error between two datasets.

    ``primary`` is the reference: value = mean over shared buses of
    ``|comparison - primary| / |primary|``, skipping zero-valued buses.

    See oedisi library for the "definitive" calculation.
    """
    primary_table = _read_result_table(user, run_id, primary)
    comparison_table = _read_result_table(user, run_id, comparison)
    shared_columns = [
        name
        for name in primary_table.column_names
        if name != "time" and name in set(comparison_table.column_names)
    ]
    comparison_rows = _rows_by_time(comparison_table)
    data: list[dict[str, Any]] = []
    for time, row in _rows_by_time(primary_table).items():
        other = comparison_rows.get(time)
        if other is None:
            continue
        errors = [
            abs(other[name] - row[name]) / abs(row[name])
            for name in shared_columns
            if isinstance(row[name], (int, float))
            and isinstance(other[name], (int, float))
            and row[name] != 0
        ]
        if errors:
            data.append({"time": time, "value": sum(errors) / len(errors)})
    return {"metric": "MARE", "columns": shared_columns, "data": data}


@app.get("/api/runs/{run_id}/topology")
def get_topology(run_id: RunId, user: CurrentUser) -> dict[str, Any] | None:
    """Feeder topology minus the bulky admittance matrix.

    Dropping ``admittance`` cuts ~99% of the ~1 MB file, which matters
    when the server isn't on localhost.
    """
    run_dir = _user_runs_dir(user) / run_id
    # Shallow globs only: component .venvs and state_estimator test fixtures
    # deeper in the tree also contain topology.json files.
    topo_files = sorted(run_dir.glob("*/topology.json")) or sorted(
        run_dir.glob("build/*/topology.json")
    )
    if not topo_files:
        return
    topo = json.loads(topo_files[0].read_text())
    topo.pop("admittance", None)
    return topo


@app.delete("/api/runs/{run_id}")
def kill_run(run_id: RunId, user: CurrentUser) -> dict[str, bool]:
    record = _get_owned_run(run_id, user)
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
