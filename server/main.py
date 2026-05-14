"""FastAPI server for the OEDISI frontend app.

Replaces the legacy Express server (`index.js` + `database.js`). Two endpoint
groups:

* `/api/templates` — file-based template CRUD (parity with the JS server).
* `/api/runs` — build an oedisi runner config in-process and launch a HELICS
  simulation subprocess.

See `CLAUDE.md` in this folder for the design rationale.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
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
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


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
        from datetime import datetime, timezone

        template["createdAt"] = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

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
    proc: subprocess.Popen
    started_at: datetime
    template_id: str | None
    run_dir: Path
    name: str


# In-memory only; lost on restart. See CLAUDE.md.
runs: dict[str, RunRecord] = {}


@app.post("/api/runs")
def start_run(
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

    proc = subprocess.Popen(
        ["helics", "run", f"--path={build_dir / 'system_runner.json'}"],
        cwd=build_dir,
    )
    runs[run_id] = RunRecord(
        proc=proc,
        started_at=datetime.now(timezone.utc),
        template_id=template_id,
        run_dir=run_dir,
        name=wiring_diagram.name,
    )
    return {"run_id": run_id}


def _serialize_run(run_id: str, record: RunRecord) -> dict[str, Any]:
    code = record.proc.poll()
    out: dict[str, Any] = {
        "run_id": run_id,
        "name": record.name,
        "started_at": record.started_at.isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        ),
        "template_id": record.template_id,
        "run_dir": str(record.run_dir),
    }
    if code is None:
        out["status"] = "running"
    else:
        out["status"] = "done" if code == 0 else "failed"
        out["exit_code"] = code
    return out


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    # Newest first, by start time. In-memory only — restart wipes this list.
    return sorted(
        (_serialize_run(rid, rec) for rid, rec in runs.items()),
        key=lambda r: r["started_at"],
        reverse=True,
    )


@app.get("/api/runs/{run_id}")
def run_status(run_id: str) -> dict[str, Any]:
    record = runs.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run_id, record)


@app.get("/api/runs/{run_id}/logs/{component}")
def run_log(run_id: str, component: str) -> PlainTextResponse:
    # Guard against path traversal — component name is a filename segment only.
    if "/" in component or "\\" in component or ".." in component:
        raise HTTPException(status_code=400, detail="Invalid component name")

    log_path = RUNS_DIR / run_id / "build" / f"{component}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return PlainTextResponse(log_path.read_text(encoding="utf-8", errors="replace"))


@app.delete("/api/runs/{run_id}")
def kill_run(run_id: str) -> dict[str, bool]:
    record = runs.pop(run_id, None)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if record.proc.poll() is None:
        record.proc.kill()
    return {"success": True}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    uvicorn.run("main:app", host="127.0.0.1", port=3001, reload=True)


if __name__ == "__main__":
    main()
