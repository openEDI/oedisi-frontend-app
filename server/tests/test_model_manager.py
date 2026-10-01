import json
import zipfile
from pathlib import Path

import pytest

from model_manager import (
    ModelManagerError,
    detect_model_format,
    resolve_model_references,
    stage_model_upload,
)


def test_detects_gdm_json(tmp_path: Path) -> None:
    (tmp_path / "system.json").write_text(json.dumps({"uuid": "system", "components": []}))

    detected = detect_model_format(tmp_path)

    assert detected.format == "gdm"
    assert detected.entrypoint == tmp_path / "system.json"


def test_detects_opendss_by_content(tmp_path: Path) -> None:
    master = tmp_path / "network.dss"
    master.write_text("new circuit.test\nnew vsource.source bus1=sourcebus\n")

    detected = detect_model_format(tmp_path)

    assert detected.format == "opendss"
    assert detected.entrypoint == master


def test_detects_cim_xml(tmp_path: Path) -> None:
    model = tmp_path / "model.xml"
    model.write_text('<rdf:RDF xmlns:cim="http://iec.ch/TC57/CIM100#"></rdf:RDF>')

    detected = detect_model_format(tmp_path)

    assert detected.format == "cim"
    assert detected.entrypoint == model


def test_detects_cyme_and_load_model_ids(tmp_path: Path) -> None:
    (tmp_path / "Network.txt").write_text("[NODE]\n[SECTION]\n")
    (tmp_path / "Equipment.txt").write_text("[CONDUCTOR]\n")
    (tmp_path / "Load.txt").write_text(
        "[CUSTOMER LOADS]\n"
        "FORMAT_CUSTOMERLOADS=SectionID,LoadModelID\n"
        "LOAD1,normal\n"
        "LOAD2,high\n"
    )

    detected = detect_model_format(tmp_path)

    assert detected.format == "cyme"
    assert detected.load_model_ids == ["high", "normal"]


def test_rejects_zip_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../../outside.txt", "unsafe")

    with pytest.raises(ModelManagerError, match="unsafe path"):
        stage_model_upload(archive.read_bytes(), "unsafe.zip", tmp_path / "models", "dev")


def test_resolves_model_id_to_component_artifact(tmp_path: Path) -> None:
    models_root = tmp_path / "models"
    model_root = models_root / "dev" / "model-1"
    artifact_root = model_root / "artifacts" / "opendss"
    sensor_root = model_root / "artifacts" / "sensors"
    artifact_root.mkdir(parents=True)
    sensor_root.mkdir(parents=True)
    (artifact_root / "Master.dss").write_text("new circuit.test")
    (sensor_root / "voltage_ids.json").write_text("[\"bus.1\"]")
    (model_root / "model.json").write_text(
        json.dumps(
            {
                "id": "model-1",
                "name": "Test feeder",
                "source_format": "cim",
                "status": "ready",
                "artifacts": {"opendss": {"entrypoint": "Master.dss"}},
            }
        )
    )

    resolved, references = resolve_model_references(
        {
            "name": "test",
            "components": [
                {
                    "name": "feeder",
                    "type": "Feeder",
                    "parameters": {"model_id": "model-1", "start_date": "2026-01-01 00:00:00"},
                },
                {
                    "name": "sensor_voltage_real",
                    "type": "MeasurementComponent",
                    "parameters": {"name": "sensor_voltage_real", "measurement_file": "legacy.json"},
                },
            ],
            "links": [],
        },
        models_root,
        "dev",
        tmp_path / "run" / "build",
    )

    parameters = resolved["components"][0]["parameters"]
    assert "model_id" not in parameters
    assert parameters["existing_feeder_file"] == "opendss/Master.dss"
    assert (tmp_path / "run" / "build" / "feeder" / "opendss" / "Master.dss").exists()
    assert resolved["components"][1]["parameters"]["measurement_file"] == "../feeder/sensors/voltage_ids.json"
    assert references[0]["model_id"] == "model-1"
