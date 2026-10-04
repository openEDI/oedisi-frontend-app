from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from postprocess import od
from postprocess import report


class OdReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def _make_run(self, player_type: str = "PlayerComponent") -> Path:
        root = Path(self._temp_dir.name)
        run_dir = root / "run"
        (run_dir / "build" / "player").mkdir(parents=True)
        (run_dir / "outputs").mkdir()

        pd.DataFrame(
            {
                "time": [
                    "2025-01-01T00:00:00",
                    "2025-01-01T00:00:01",
                    "2025-01-01T00:00:02",
                ],
                "frequency_hz": [60.0, 60.01, 59.99],
            }
        ).to_csv(run_dir / "build" / "player" / "signal.csv", index=False)

        pd.DataFrame(
            {
                "event_id": [1],
                "time": ["2025-01-01T00:00:01"],
                "start_time_sec": [1.0],
                "reporting_time_sec": [1.1],
                "n_voted_units": [1],
                "mode_0_freq_hz": [1.0],
                "mode_0_damping": [0.01],
                "mode_0_amp": [0.03],
            }
        ).to_feather(run_dir / "outputs" / "events.feather")

        wiring = {
            "name": "OD report test",
            "components": [
                {
                    "name": "player",
                    "type": player_type,
                    "parameters": {
                        "filename": "/components/ornl-od-prony/data/signal.csv",
                        "number_of_timesteps": 3,
                        "run_freq_time_step": 1.0,
                    },
                },
                {
                    "name": "od",
                    "type": "ODComponent",
                    "parameters": {
                        "ground_truth_json": json.dumps(
                            [
                                {
                                    "start_time_sec": 1.0,
                                    "frequency_hz": 1.0,
                                    "amplitude": 0.03,
                                    "damping_ratio": 0.01,
                                }
                            ]
                        )
                    },
                },
            ],
            "links": [],
        }
        (run_dir / "wiring.json").write_text(json.dumps(wiring), encoding="utf-8")
        return run_dir

    def test_current_player_component_loads_measured_signal(self) -> None:
        signal = od._signal(self._make_run())

        self.assertIsNotNone(signal)
        assert signal is not None
        time_s, deviation_mhz, label = signal
        self.assertEqual(time_s.tolist(), [0.0, 1.0, 2.0])
        self.assertEqual(len(deviation_mhz), 3)
        self.assertEqual(label, "frequency hz")

    def test_legacy_player_type_remains_supported(self) -> None:
        self.assertIsNotNone(od._signal(self._make_run("Player")))

    def test_portable_ornl_od_path_resolves_component_asset(self) -> None:
        run_dir = self._make_run()
        source = run_dir / "build" / "player" / "signal.csv"
        component_root = Path(self._temp_dir.name) / "components"
        target = component_root / "ornl-od-prony" / "data" / "signal.csv"
        target.parent.mkdir(parents=True)
        source.replace(target)

        with patch.dict(os.environ, {"OEDISI_COMPONENTS": str(component_root)}):
            self.assertIsNotNone(od._signal(run_dir))

    def test_measured_and_event_timelines_are_first_and_second(self) -> None:
        _title, sections = od.build_sections(self._make_run())

        self.assertEqual(
            [heading for heading, _html in sections[:2]],
            ["Detection timeline (measured signal)", "Detection timeline"],
        )
        self.assertIn("<img", sections[0][1])
        self.assertIn("<img", sections[1][1])

    def test_missing_signal_keeps_event_timeline(self) -> None:
        run_dir = self._make_run()
        (run_dir / "build" / "player" / "signal.csv").unlink()

        _title, sections = od.build_sections(run_dir)

        self.assertEqual(sections[0][0], "Detection timeline")

    def test_od_report_context_invalidates_legacy_cache(self) -> None:
        run_dir = self._make_run()

        self.assertEqual(
            report._context_for("od", run_dir),
            od.REPORT_CONTEXT_VERSION,
        )
        self.assertNotEqual(report._context_for("od", run_dir), "")


if __name__ == "__main__":
    unittest.main()
