from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

import main


class RunAvailabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        main.runs.clear()

    def tearDown(self) -> None:
        main.runs.clear()

    def test_available_without_active_run_or_broker(self) -> None:
        with patch.object(main, "_port_in_use", return_value=False):
            self.assertTrue(main._run_slot_available())
            self.assertEqual(
                main.run_availability("tester"),
                {"available": True, "retry_after_seconds": 5},
            )

    def test_in_memory_run_is_busy_without_exposing_details(self) -> None:
        main.runs["private-run-id"] = main.RunRecord(
            pid=123,
            user="another-lab",
            started_at=datetime.now(timezone.utc),
            template_id="private-template",
            run_dir=Path("private"),
            name="Private simulation name",
            status="running",
        )
        with patch.object(main, "_port_in_use", return_value=False):
            self.assertEqual(
                main.run_availability("tester"),
                {"available": False, "retry_after_seconds": 5},
            )
            with self.assertRaises(HTTPException) as raised:
                main._assert_no_run_in_progress()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, main.RUN_BUSY_DETAIL)
        self.assertNotIn("Private", raised.exception.detail)
        self.assertNotIn("another-lab", raised.exception.detail)

    def test_external_broker_is_busy(self) -> None:
        with patch.object(main, "_port_in_use", side_effect=lambda port: port == 23404):
            self.assertFalse(main._run_slot_available())
            with self.assertRaises(HTTPException) as raised:
                main._assert_no_run_in_progress()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, main.RUN_BUSY_DETAIL)


class ConcurrentLaunchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        main.runs.clear()
        self.temporary = tempfile.TemporaryDirectory()
        self.addAsyncCleanup(self._cleanup)

    async def _cleanup(self) -> None:
        for task in tuple(main._watcher_tasks):
            task.cancel()
        if main._watcher_tasks:
            await asyncio.gather(*tuple(main._watcher_tasks), return_exceptions=True)
        main.runs.clear()
        self.temporary.cleanup()

    async def test_second_near_simultaneous_launch_gets_clear_409(self) -> None:
        spawn_entered = asyncio.Event()
        release_spawn = asyncio.Event()
        finish_process = asyncio.Event()

        class FakeProcess:
            pid = 456789

            async def wait(self) -> int:
                await finish_process.wait()
                return 0

        async def fake_spawn(*_args, **_kwargs):
            spawn_entered.set()
            await release_spawn.wait()
            return FakeProcess()

        def fake_build(_wiring, build_dir: Path) -> None:
            build_dir.mkdir(parents=True)

        diagram = main.AppWiringDiagram(name="first", components=[], links=[])
        with (
            patch.object(main, "RUNS_DIR", Path(self.temporary.name)),
            patch.object(main, "build_runner", side_effect=fake_build),
            patch.object(main.asyncio, "create_subprocess_exec", side_effect=fake_spawn),
            patch.object(main, "_port_in_use", return_value=False),
            patch.object(main, "_tree_kill"),
        ):
            first = asyncio.create_task(main.start_run(diagram, "user-one", "one"))
            await asyncio.wait_for(spawn_entered.wait(), timeout=2)
            with self.assertRaises(HTTPException) as raised:
                await main.start_run(diagram, "user-two", "two")
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(raised.exception.detail, main.RUN_BUSY_DETAIL)

            release_spawn.set()
            first_result = await asyncio.wait_for(first, timeout=2)
            self.assertIn("run_id", first_result)
            finish_process.set()
            await asyncio.sleep(0)

    async def test_watcher_cleans_process_group_after_runner_failure(self) -> None:
        run_dir = Path(self.temporary.name) / "failed-run"
        run_dir.mkdir(parents=True)
        main.runs["failed-run"] = main.RunRecord(
            pid=456790,
            user="user-one",
            started_at=datetime.now(timezone.utc),
            template_id="template-one",
            run_dir=run_dir,
            name="failed",
            status="running",
        )

        class FailedProcess:
            pid = 456790

            async def wait(self) -> int:
                return 1

        with (
            patch.object(main, "_max_run_seconds", return_value=None),
            patch.object(main, "_tree_kill") as kill_group,
        ):
            await main._watch_proc("failed-run", FailedProcess())

        kill_group.assert_called_once_with(456790)
        self.assertEqual(main.runs["failed-run"].status, "failed")
        self.assertEqual(main.runs["failed-run"].exit_code, 1)


if __name__ == "__main__":
    unittest.main()
