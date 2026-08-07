from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import nbformat
import pytest
from fastapi import HTTPException

import main as server_main


@pytest.fixture(autouse=True)
def _isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    templates_dir = data_dir / "templates"
    runs_dir = tmp_path / "runs"
    monkeypatch.setattr(server_main, "DATA_DIR", data_dir)
    monkeypatch.setattr(server_main, "TEMPLATES_DIR", templates_dir)
    monkeypatch.setattr(server_main, "RUNS_DIR", runs_dir)
    server_main.runs.clear()
    yield
    server_main.runs.clear()


def _write_template_json(user: str, template_id: str) -> None:
    template = {
        "id": template_id,
        "name": "Test Template",
        "description": "desc",
        "createdAt": "2026-01-01T00:00:00.000Z",
        "nodes": [],
        "edges": [],
    }
    path = server_main._user_templates_dir(user) / f"{template_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    server_main._atomic_write_json(path, template)


def _write_notebook(path: Path, code: str) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell(code)]
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, str(path))


def test_delete_template_removes_template_notebook_artifacts() -> None:
    user = "dev"
    template_id = "1783971109414"
    _write_template_json(user, template_id)

    template_nb_path = server_main._template_notebook_path(user, template_id)
    _write_notebook(template_nb_path, 'DATA_DIR = r""')
    assert template_nb_path.exists()

    resp = server_main.delete_template(template_id, user)

    assert resp["success"] is True
    assert not server_main._template_path(user, template_id).exists()
    assert not template_nb_path.parent.exists()


def test_create_notebook_copies_from_template_and_status() -> None:
    user = "dev"
    template_id = "1779415501591"
    run_id = "f2db947fbbcd41f58fcfab68857ef972"
    _write_template_json(user, template_id)

    run_dir = server_main._user_runs_dir(user) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "build").mkdir(parents=True, exist_ok=True)

    template_nb_path = server_main._template_notebook_path(user, template_id)
    _write_notebook(
        template_nb_path,
        '# copied from template\nDATA_DIR = r""\nprint(DATA_DIR)',
    )

    server_main.runs[run_id] = server_main.RunRecord(
        pid=1,
        user=user,
        started_at=datetime.now(timezone.utc),
        template_id=template_id,
        run_dir=run_dir,
        name="run",
        status="done",
    )

    created = server_main.create_notebook(run_id, user)
    status = server_main.get_notebook_status(run_id, user)

    assert created["exists"] is True
    assert created["created"] is True
    assert status["exists"] is True
    assert status["jupyter_url"].endswith(f"/{user}/{run_id}/notebook.ipynb")

    run_nb_path = server_main._notebook_path(user, run_id)
    nb = nbformat.read(str(run_nb_path), as_version=4)
    code_cell_source = "\n".join(
        cell.source for cell in nb.cells if cell.cell_type == "code"
    )
    assert f'DATA_DIR = r"{run_dir / "build"}"' in code_cell_source


def test_save_notebook_to_template_strips_run_specific_data_dir() -> None:
    user = "dev"
    template_id = "1779415501597"
    run_id = "a0c2b1409f674e3396b62f442fa2b25e"
    _write_template_json(user, template_id)

    run_dir = server_main._user_runs_dir(user) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_nb_path = server_main._notebook_path(user, run_id)
    _write_notebook(
        run_nb_path,
        f'DATA_DIR = r"{run_dir / "build"}"\nprint(DATA_DIR)',
    )

    server_main.runs[run_id] = server_main.RunRecord(
        pid=2,
        user=user,
        started_at=datetime.now(timezone.utc),
        template_id=template_id,
        run_dir=run_dir,
        name="run",
        status="done",
    )

    resp = server_main.save_notebook_to_template(run_id, user)
    assert resp["success"] is True

    template_nb_path = server_main._template_notebook_path(user, template_id)
    nb = nbformat.read(str(template_nb_path), as_version=4)
    code_cell_source = "\n".join(
        cell.source for cell in nb.cells if cell.cell_type == "code"
    )
    assert 'DATA_DIR = r""' in code_cell_source


def test_save_notebook_to_template_rejects_run_without_template() -> None:
    user = "dev"
    run_id = "0b1d274c53f54971bd823c595ceb9773"
    run_dir = server_main._user_runs_dir(user) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_notebook(server_main._notebook_path(user, run_id), 'DATA_DIR = r""')

    server_main.runs[run_id] = server_main.RunRecord(
        pid=3,
        user=user,
        started_at=datetime.now(timezone.utc),
        template_id=None,
        run_dir=run_dir,
        name="run",
        status="done",
    )

    with pytest.raises(HTTPException) as exc:
        server_main.save_notebook_to_template(run_id, user)

    assert exc.value.status_code == 400


def test_start_notebook_server_single_user_uses_jupyterlab(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeProc:
        pid = 12345

    captured: dict[str, object] = {}

    async def fake_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.delenv("OEDISI_MULTI_USER", raising=False)
    monkeypatch.setattr(server_main.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(server_main, "RUNS_DIR", tmp_path / "runs")

    proc = asyncio.run(server_main._start_jupyter())

    assert proc is not None
    assert proc.pid == 12345
    args = captured["args"]
    kwargs = captured["kwargs"]
    assert "jupyterlab" in args
    assert "--IdentityProvider.token=" in args
    assert kwargs["stdout"] is asyncio.subprocess.DEVNULL
    assert kwargs["stderr"] is asyncio.subprocess.DEVNULL


def test_start_notebook_server_multi_user_uses_voila(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeProc:
        pid = 12346

    captured: dict[str, object] = {}

    async def fake_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.setenv("OEDISI_MULTI_USER", "1")
    monkeypatch.setattr(server_main.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(server_main, "RUNS_DIR", tmp_path / "runs")

    proc = asyncio.run(server_main._start_jupyter())

    assert proc is not None
    assert proc.pid == 12346
    args = captured["args"]
    kwargs = captured["kwargs"]
    assert "voila" in args
    assert "--Voila.ip=127.0.0.1" in args
    assert kwargs["stdout"] is asyncio.subprocess.DEVNULL
    assert kwargs["stderr"] is asyncio.subprocess.DEVNULL


def test_notebook_urls_single_user_use_jupyterlab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OEDISI_MULTI_USER", raising=False)
    assert server_main._jupyter_notebook_url("dev", "run1").startswith(
        "/jupyter/lab/tree/"
    )
    assert server_main._jupyter_template_notebook_url("dev", "t1").startswith(
        "/jupyter/lab/tree/"
    )


def test_notebook_urls_multi_user_use_voila(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OEDISI_MULTI_USER", "1")
    assert server_main._jupyter_notebook_url("alice", "run1").startswith(
        "/voila/render/"
    )
    assert server_main._jupyter_template_notebook_url("alice", "t1").startswith(
        "/voila/render/"
    )
