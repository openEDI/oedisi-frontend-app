from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from postprocess import ev


class EvReportPairingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    @staticmethod
    def _wiring(
        mode: str,
        *,
        feeder_location: str = "gadal_ieee123/qsts",
        random_seed: int = 42,
    ) -> dict:
        return {
            "components": [
                {
                    "type": "Feeder",
                    "parameters": {
                        "opendss_location": feeder_location,
                        "profile_location": "gadal_ieee123/profiles",
                        "number_of_timesteps": 96,
                        "run_freq_sec": 900,
                    },
                },
                {
                    "type": "EVCSComponent",
                    "parameters": {
                        "control_mode": mode,
                        "evcs_bus": ["48.1", "65.1", "76.1"],
                        "num_evs_per_station": [67, 67, 66],
                        "random_seed": random_seed,
                    },
                },
            ]
        }

    def _make_completed_run(self, name: str, wiring: dict) -> Path:
        run_dir = self.root / name
        outputs = run_dir / "outputs"
        outputs.mkdir(parents=True)
        (run_dir / "wiring.json").write_text(json.dumps(wiring), encoding="utf-8")
        (run_dir / "run.json").write_text(
            json.dumps({"exit_code": 0}), encoding="utf-8"
        )
        for filename in (
            "voltage_real.feather",
            "voltage_imag.feather",
            "topology.json",
        ):
            (outputs / filename).touch()
        return run_dir

    def test_scenario_signature_ignores_only_control_mode(self) -> None:
        controlled = self._wiring("dopf")
        baseline = self._wiring("uncontrolled")

        self.assertEqual(ev._scenario_sig(controlled), ev._scenario_sig(baseline))
        self.assertNotEqual(
            ev._scenario_sig(controlled),
            ev._scenario_sig(self._wiring("uncontrolled", random_seed=7)),
        )
        self.assertNotEqual(
            ev._scenario_sig(controlled),
            ev._scenario_sig(
                self._wiring("uncontrolled", feeder_location="SMART-DS/P1U")
            ),
        )

    def test_companion_requires_matching_feeder_and_ev_settings(self) -> None:
        controlled = self._make_completed_run(
            "controlled", self._wiring("dopf")
        )
        matching = self._make_completed_run(
            "matching-baseline", self._wiring("uncontrolled")
        )
        self._make_completed_run(
            "different-seed", self._wiring("uncontrolled", random_seed=7)
        )
        self._make_completed_run(
            "different-feeder",
            self._wiring("uncontrolled", feeder_location="SMART-DS/P1U"),
        )

        companion = ev._find_companion(controlled)

        self.assertIsNotNone(companion)
        assert companion is not None
        self.assertEqual(companion[0], matching)
        self.assertEqual(companion[1], "uncontrolled")


if __name__ == "__main__":
    unittest.main()