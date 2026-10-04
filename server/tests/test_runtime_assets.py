from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class RuntimeAssetTests(unittest.TestCase):
    def test_resolves_portable_component_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            components = Path(temporary)
            data = components / "pnnl-emt-swod" / "data"
            data.mkdir(parents=True)
            current = data / "i_abc.csv"
            current.touch()

            with patch.dict(os.environ, {"OEDISI_COMPONENTS": str(components)}):
                self.assertEqual(
                    main._resolve_runtime_parameter(
                        "/components/pnnl-emt-swod/data/i_abc.csv"
                    ),
                    str(current.resolve()),
                )

    def test_resolves_portable_assets_in_nested_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            components = Path(temporary)
            data = components / "ornl-od-prony" / "data"
            data.mkdir(parents=True)
            signal = data / "signal.csv"
            signal.touch()

            parameters = {
                "files": ["unchanged", "/components/ornl-od-prony/data/signal.csv"]
            }
            with patch.dict(os.environ, {"OEDISI_COMPONENTS": str(components)}):
                self.assertEqual(
                    main._resolve_runtime_parameter(parameters),
                    {"files": ["unchanged", str(signal.resolve())]},
                )

    def test_rejects_portable_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"OEDISI_COMPONENTS": temporary}):
                with self.assertRaises(ValueError):
                    main._resolve_runtime_parameter(
                        "/components/pnnl-emt-swod/../private.csv"
                    )


if __name__ == "__main__":
    unittest.main()
