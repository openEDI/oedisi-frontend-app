"""Model storage, format detection, conversion, and inspection.

The model manager deliberately keeps the model source format separate from the
artifact consumed by a simulation component.  Distribution models currently
use Ditto's GDM in-memory representation and produce an OpenDSS artifact for
the LocalFeeder component.  Other model families can add readers and target
artifacts without changing this storage contract.
"""

from __future__ import annotations

import copy
import csv
import gc
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import zipfile
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


SUPPORTED_SOURCE_FORMATS = ("gdm", "opendss", "cim", "cyme")
SENSOR_TYPES = ("voltage", "real_power", "reactive_power")
MODEL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,96}$")
USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_ARCHIVE_FILES = 20_000
MAX_ARCHIVE_UNCOMPRESSED_SIZE = 2 * 1024 * 1024 * 1024

# OpenDSSDirect keeps process-global state.  Ditto's OpenDSS reader therefore
# must not run concurrently with another OpenDSS conversion in this process.
_OPENDSS_LOCK = threading.Lock()


class ModelManagerError(ValueError):
    """Base error raised for invalid model input or conversion."""

    status_code = 400
    error_code = "invalid-model"

    def __init__(self, message: str, *, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.extra = extra or {}


class UnsupportedModelError(ModelManagerError):
    error_code = "unsupported-model-format"


class AmbiguousModelError(ModelManagerError):
    status_code = 409
    error_code = "ambiguous-model-format"


class ModelConversionError(ModelManagerError):
    status_code = 422
    error_code = "model-conversion-failed"


class ModelNotFoundError(ModelManagerError):
    status_code = 404
    error_code = "model-not-found"


@dataclass
class DetectedModel:
    format: str
    root: Path
    entrypoint: Path | None = None
    files: dict[str, Path] = field(default_factory=dict)
    load_model_ids: list[str] = field(default_factory=list)
    reason: str = ""

    def source_files(self) -> list[str]:
        return sorted(
            str(path.relative_to(self.root))
            for path in self.root.rglob("*")
            if path.is_file()
        )

    def entrypoint_name(self) -> str | None:
        if self.entrypoint is None:
            return None
        return str(self.entrypoint.relative_to(self.root))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _validate_id(value: str, *, label: str = "model id") -> None:
    if not MODEL_ID_PATTERN.fullmatch(value):
        raise ModelManagerError(f"Invalid {label}")


def _validate_user(value: str) -> None:
    if not USER_ID_PATTERN.fullmatch(value):
        raise ModelManagerError("Invalid user id")


def _normalize_format(value: str | None) -> str:
    normalized = (value or "auto").strip().lower().replace("-", "_")
    aliases = {
        "json": "gdm",
        "gdm_json": "gdm",
        "dss": "opendss",
        "open_dss": "opendss",
        "cim_iec_61968_13": "cim",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized != "auto" and normalized not in SUPPORTED_SOURCE_FORMATS:
        raise UnsupportedModelError(
            f"Unsupported requested format '{value}'. Supported formats: auto, "
            f"{', '.join(SUPPORTED_SOURCE_FORMATS)}."
        )
    return normalized


def _files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def _detect_gdm(root: Path, files: list[Path]) -> DetectedModel | None:
    candidates = [file for file in files if file.suffix.lower() == ".json"]
    candidates.sort(key=lambda file: (len(file.relative_to(root).parts), str(file)))
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and "components" in data and "uuid" in data:
            return DetectedModel(
                format="gdm",
                root=root,
                entrypoint=candidate,
                reason="Detected GDM DistributionSystem JSON.",
            )
    return None


def _detect_opendss(root: Path, files: list[Path]) -> tuple[int, DetectedModel] | None:
    candidates: list[tuple[int, Path]] = []
    for candidate in files:
        if candidate.suffix.lower() != ".dss":
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")[:128_000].lower()
        except OSError:
            continue
        stem = candidate.stem.lower()
        has_master_name = stem == "master" or stem.startswith("master_")
        has_circuit_command = "new circuit" in text or "new vsource" in text
        score = 0
        if has_master_name:
            score += 100
        if has_circuit_command:
            score += 60
        if "redirect" in text:
            score += 20
        if any(token in text for token in ("new line", "new transformer", "new load")):
            score += 10
        if score and (has_master_name or has_circuit_command):
            candidates.append((score, candidate))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise AmbiguousModelError(
            "Multiple OpenDSS master candidates were detected; upload one model archive "
            "or specify the OpenDSS entrypoint explicitly."
        )
    score, entrypoint = candidates[0]
    return score, DetectedModel(
        format="opendss",
        root=root,
        entrypoint=entrypoint,
        reason="Detected an OpenDSS master file from DSS commands.",
    )


def _detect_cim(root: Path, files: list[Path]) -> tuple[int, DetectedModel] | None:
    candidates: list[tuple[int, Path]] = []
    for candidate in files:
        if candidate.suffix.lower() not in {".xml", ".rdf"}:
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")[:128_000]
        except OSError:
            continue
        lowered = text.lower()
        if "rdf:rdf" not in lowered or not ("cim:" in lowered or "xmlns:cim" in lowered):
            continue
        score = 120 if "iec61970" in lowered or "iec61968" in lowered else 100
        candidates.append((score, candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda item: str(item[1]))
    if len(candidates) > 1:
        raise AmbiguousModelError(
            "Multiple CIM/XML model files were detected; upload one CIM model at a time."
        )
    score, entrypoint = candidates[0]
    return score, DetectedModel(
        format="cim",
        root=root,
        entrypoint=entrypoint,
        reason="Detected RDF/XML with CIM namespaces.",
    )


def _extract_cyme_load_model_ids(load_file: Path) -> list[str]:
    try:
        lines = load_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []

    in_customer_loads = False
    columns: list[str] = []
    ids: set[str] = set()
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("["):
            in_customer_loads = lowered == "[customer loads]"
            columns = []
            continue
        if not in_customer_loads or not stripped:
            continue
        if lowered.startswith("format_customerloads="):
            columns = [column.strip().lower() for column in stripped.split("=", 1)[1].split(",")]
            continue
        if not columns or stripped.lower().startswith("format_"):
            continue
        values = next(csv.reader([stripped]))
        if "loadmodelid" not in columns:
            continue
        index = columns.index("loadmodelid")
        if len(values) > index and values[index].strip():
            ids.add(values[index].strip())
    return sorted(ids)


def _detect_cyme(root: Path, files: list[Path]) -> DetectedModel | None:
    grouped: dict[Path, dict[str, Path]] = {}
    required = {"network.txt": "network", "equipment.txt": "equipment", "load.txt": "load"}
    for file in files:
        key = required.get(file.name.lower())
        if key:
            grouped.setdefault(file.parent, {})[key] = file

    complete = [
        (directory, group)
        for directory, group in grouped.items()
        if set(group) == set(required.values())
    ]
    if not complete:
        return None
    if len(complete) > 1:
        raise AmbiguousModelError("Multiple CYME Network.txt/Equipment.txt/Load.txt file sets were detected.")

    directory, group = complete[0]
    network_text = group["network"].read_text(encoding="utf-8", errors="ignore")[:64_000]
    if "[node]" not in network_text.lower() or "[section]" not in network_text.lower():
        return None
    return DetectedModel(
        format="cyme",
        root=root,
        files=group,
        load_model_ids=_extract_cyme_load_model_ids(group["load"]),
        reason="Detected CYME Network.txt, Equipment.txt, and Load.txt files.",
    )


def detect_model_format(root: Path | str, requested_format: str = "auto") -> DetectedModel:
    path = Path(root)
    if not path.is_dir():
        raise ModelManagerError(f"Model staging directory does not exist: {path}")
    files = _files(path)
    normalized = _normalize_format(requested_format)

    detectors = {
        "gdm": _detect_gdm,
        "opendss": _detect_opendss,
        "cim": _detect_cim,
        "cyme": _detect_cyme,
    }
    if normalized != "auto":
        detected = detectors[normalized](path, files)
        if detected is None:
            raise UnsupportedModelError(f"Input does not contain a valid {normalized} model.")
        return detected[1] if isinstance(detected, tuple) else detected

    gdm = _detect_gdm(path, files)
    if gdm is not None:
        return gdm
    candidates: list[tuple[int, DetectedModel]] = []
    for detector in (_detect_cyme, _detect_opendss, _detect_cim):
        result = detector(path, files)
        if result is None:
            continue
        if isinstance(result, tuple):
            candidates.append(result)
        else:
            candidates.append((120, result))
    if not candidates:
        raise UnsupportedModelError(
            "Could not detect a supported model. Expected GDM JSON, an OpenDSS master "
            "file, CIM/IEC 61968-13 XML, or a CYME Network/Equipment/Load file set."
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        formats = ", ".join(sorted({candidate.format for _, candidate in candidates}))
        raise AmbiguousModelError(
            f"Input matches multiple model formats ({formats}); specify the format explicitly."
        )
    return candidates[0][1]


def _load_gdm(entrypoint: Path):
    try:
        from gdm.distribution import DistributionSystem
        from gdm.distribution.upgrade_handler.upgrade_handler import UpgradeHandler
    except ImportError as exc:  # pragma: no cover - dependency packaging failure
        raise ModelConversionError("grid-data-models is not installed; GDM conversion is unavailable.") from exc
    return DistributionSystem.from_json(entrypoint, upgrade_handler=UpgradeHandler().upgrade)


def _load_system(detected: DetectedModel, crs: str | None, load_model_id: str | None):
    try:
        if detected.format == "gdm":
            return _load_gdm(detected.entrypoint), None, "gdm"
        if detected.format == "opendss":
            from ditto.readers.opendss.reader import Reader

            with _OPENDSS_LOCK:
                # Some OpenDSS models contain Export commands.  Ditto invokes
                # OpenDSSDirect in-process, so isolate its process-relative
                # output in a temporary directory instead of polluting the
                # backend working directory.
                previous_cwd = Path.cwd()
                with tempfile.TemporaryDirectory(prefix="oedisi-opendss-") as temporary_cwd:
                    os.chdir(temporary_cwd)
                    try:
                        reader = Reader(detected.entrypoint, crs=crs) if crs else Reader(detected.entrypoint)
                    finally:
                        os.chdir(previous_cwd)
                return reader.get_system(), reader, "opendss"
        if detected.format == "cim":
            from ditto.readers.cim_iec_61968_13.reader import Reader

            reader = Reader(detected.entrypoint)
            reader.read()
            return reader.get_system(), reader, "cim_iec_61968_13"
        if detected.format == "cyme":
            if len(detected.load_model_ids) > 1 and not load_model_id:
                raise AmbiguousModelError(
                    "CYME input contains multiple LoadModelID values: "
                    f"{', '.join(detected.load_model_ids)}. Select one before importing.",
                    extra={"available_load_model_ids": detected.load_model_ids},
                )
            if load_model_id and detected.load_model_ids and load_model_id not in detected.load_model_ids:
                raise ModelManagerError(
                    f"Unknown CYME load_model_id '{load_model_id}'. Available values: "
                    f"{', '.join(detected.load_model_ids)}."
                )
            from ditto.readers.cyme.reader import Reader

            reader = Reader(
                detected.files["network"],
                detected.files["equipment"],
                detected.files["load"],
                load_model_id=load_model_id,
            )
            return reader.get_system(), reader, "cyme"
    except ModelManagerError:
        raise
    except Exception as exc:
        raise ModelConversionError(f"Failed to read {detected.format} model: {exc}") from exc
    raise UnsupportedModelError(f"Unsupported model format: {detected.format}")


def _reader_warnings(reader: Any) -> list[str]:
    if reader is None:
        return []
    warnings = getattr(reader, "validation_errors", [])
    return [" | ".join(str(value) for value in warning) for warning in warnings]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump(mode="json"))
        except Exception:
            pass
    return str(value)


def inspect_system(system: Any) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for component in system.iter_all_components():
        component_type = type(component).__name__
        counts[component_type] = counts.get(component_type, 0) + 1
        try:
            data = component.model_dump(mode="json")
        except Exception:
            data = {"name": getattr(component, "name", "")}
        serialized = _json_safe(data)
        if not isinstance(serialized, dict):
            serialized = {"value": serialized}
        serialized["_type"] = component_type
        serialized.setdefault("uuid", str(getattr(component, "uuid", "")))
        serialized.setdefault("name", str(getattr(component, "name", "")))
        components.append(serialized)

    graph = system.get_undirected_graph()
    nodes = []
    for node, data in graph.nodes(data=True):
        nodes.append({"id": str(node), **_json_safe(data)})
    edges = []
    for source, target, data in graph.edges(data=True):
        edges.append({"source": str(source), "target": str(target), **_json_safe(data)})

    summary = {
        "name": str(getattr(system, "name", "") or ""),
        "uuid": str(getattr(system, "uuid", "") or ""),
        "description": str(getattr(system, "description", "") or ""),
        "total_components": len(components),
        "component_types": dict(sorted(counts.items())),
        "topology_nodes": len(nodes),
        "topology_edges": len(edges),
    }
    return {"summary": summary, "components": components, "topology": {"nodes": nodes, "edges": edges}}


def _dss_bus_name(value: str) -> str:
    return value.split(".", 1)[0]


def _dss_value(callable_value: Any, default: Any = None) -> Any:
    try:
        return _json_safe(callable_value())
    except Exception:
        return default


def inspect_opendss_model(entrypoint: Path | str) -> dict[str, Any]:
    """Inspect the generated OpenDSS artifact, not the conversion IR.

    This is the inspection contract used by the UI.  Ditto/GDM is still used
    during conversion, but buses, elements, properties, topology, and physics
    shown to a user are read back from the actual DSS circuit.
    """

    try:
        import opendssdirect as dss
    except ImportError as exc:  # pragma: no cover - dependency packaging failure
        raise ModelConversionError("OpenDSSDirect is not installed; DSS inspection is unavailable.") from exc

    master = Path(entrypoint).resolve()
    if not master.is_file():
        raise ModelConversionError(f"OpenDSS entrypoint does not exist: {master}")

    with _OPENDSS_LOCK:
        previous_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory(prefix="oedisi-dss-inspection-") as temporary_cwd:
                os.chdir(temporary_cwd)
                dss.Basic.Start(0)
                with redirect_stdout(io.StringIO()):
                    dss.Text.Command(f'Compile "{master}"')

                bus_names = list(dss.Circuit.AllBusNames())
                element_names = list(dss.Circuit.AllElementNames())
                buses: list[dict[str, Any]] = []
                for bus_name in bus_names:
                    dss.Circuit.SetActiveBus(bus_name)
                    buses.append(
                        {
                            "id": bus_name,
                            "name": bus_name,
                            "nodes": _dss_value(dss.Bus.Nodes, []),
                            "kv_base": _dss_value(dss.Bus.kVBase),
                            "x": _dss_value(dss.Bus.X),
                            "y": _dss_value(dss.Bus.Y),
                            "voltage_mag_angle": _dss_value(dss.Bus.VMagAngle, []),
                            "pu_voltage_mag_angle": _dss_value(dss.Bus.puVmagAngle, []),
                            "pde_elements": _dss_value(dss.Bus.AllPDEatBus, []),
                            "pce_elements": _dss_value(dss.Bus.AllPCEatBus, []),
                        }
                    )

                elements: list[dict[str, Any]] = []
                class_counts: dict[str, int] = {}
                topology_edges: list[dict[str, Any]] = []
                for element_name in element_names:
                    dss.Circuit.SetActiveElement(element_name)
                    element_class = element_name.split(".", 1)[0]
                    class_counts[element_class] = class_counts.get(element_class, 0) + 1
                    property_names = list(dss.CktElement.AllPropertyNames())
                    properties: dict[str, Any] = {}
                    for index, property_name in enumerate(property_names, 1):
                        try:
                            properties[property_name] = _json_safe(dss.Properties.Value(index))
                        except Exception:
                            properties[property_name] = None
                    bus_connections = _dss_value(dss.CktElement.BusNames, []) or []
                    element = {
                        "id": element_name,
                        "name": element_name.split(".", 1)[1] if "." in element_name else element_name,
                        "class": element_class,
                        "enabled": _dss_value(dss.CktElement.Enabled),
                        "num_phases": _dss_value(dss.CktElement.NumPhases),
                        "num_terminals": _dss_value(dss.CktElement.NumTerminals),
                        "bus_names": bus_connections,
                        "properties": properties,
                        "powers": _dss_value(dss.CktElement.Powers, []),
                        "losses": _dss_value(dss.CktElement.Losses, []),
                        "voltages_mag_angle": _dss_value(dss.CktElement.VoltagesMagAng, []),
                    }
                    elements.append(element)
                    if len(bus_connections) > 1:
                        source = _dss_bus_name(bus_connections[0])
                        for terminal, bus_connection in enumerate(bus_connections[1:], 2):
                            target = _dss_bus_name(bus_connection)
                            topology_edges.append(
                                {
                                    "id": f"{element_name}::terminal-{terminal}",
                                    "source": source,
                                    "target": target,
                                    "element": element_name,
                                    "class": element_class,
                                    "terminal": terminal,
                                }
                            )

                pu_voltages = _dss_value(dss.Circuit.AllBusMagPu, []) or []
                pu_voltages = [float(value) for value in pu_voltages if isinstance(value, (int, float))]
                total_power = _dss_value(dss.Circuit.TotalPower, []) or []
                losses = _dss_value(dss.Circuit.Losses, []) or []
                summary = {
                    "name": str(_dss_value(dss.Circuit.Name, "") or ""),
                    "uuid": "",
                    "description": "",
                    "source_of_truth": "opendss",
                    "total_components": len(elements),
                    "element_count": len(elements),
                    "bus_count": len(buses),
                    "element_types": dict(sorted(class_counts.items())),
                    "component_types": dict(sorted(class_counts.items())),
                    "topology_nodes": len(buses),
                    "topology_edges": len(topology_edges),
                }
                bus_by_name = {bus["name"]: bus for bus in buses}
                geojson_features: list[dict[str, Any]] = []
                coordinate_pairs: list[tuple[float, float]] = []
                for bus in buses:
                    x, y = bus.get("x"), bus.get("y")
                    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                        continue
                    if x == 0 and y == 0:
                        continue
                    coordinate_pairs.append((float(x), float(y)))
                    geojson_features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [x, y]},
                            "properties": {
                                "kind": "bus",
                                "id": bus["id"],
                                "name": bus["name"],
                                "nodes": bus["nodes"],
                                "kv_base": bus.get("kv_base"),
                            },
                        }
                    )
                for edge in topology_edges:
                    source = bus_by_name.get(edge["source"])
                    target = bus_by_name.get(edge["target"])
                    if not source or not target:
                        continue
                    source_xy = [source.get("x"), source.get("y")]
                    target_xy = [target.get("x"), target.get("y")]
                    if any(not isinstance(value, (int, float)) for value in (*source_xy, *target_xy)):
                        continue
                    if source_xy == [0, 0] or target_xy == [0, 0]:
                        continue
                    geojson_features.append(
                        {
                            "type": "Feature",
                            "geometry": {"type": "LineString", "coordinates": [source_xy, target_xy]},
                            "properties": {
                                "kind": "element",
                                "id": edge["id"],
                                "element": edge["element"],
                                "class": edge["class"],
                                "source": edge["source"],
                                "target": edge["target"],
                            },
                        }
                    )
                coordinates_are_geographic = bool(coordinate_pairs) and all(
                    -180 <= x <= 180 and -90 <= y <= 90 for x, y in coordinate_pairs
                )
                return {
                    "source_of_truth": "opendss",
                    "format": "opendss",
                    "entrypoint": master.name,
                    "coordinate_mode": "gis" if coordinates_are_geographic else "local",
                    "coordinate_reference_system": "EPSG:4326" if coordinates_are_geographic else None,
                    "summary": summary,
                    "buses": buses,
                    "elements": elements,
                    "topology": {
                        "nodes": [{"id": bus["id"], "name": bus["name"]} for bus in buses],
                        "edges": topology_edges,
                    },
                    "geojson": {
                        "type": "FeatureCollection",
                        "coordinate_reference_system": "EPSG:4326" if coordinates_are_geographic else None,
                        "coordinate_mode": "gis" if coordinates_are_geographic else "local",
                        "features": geojson_features,
                    },
                    "physics": {
                        "solution": {
                            "converged": bool(_dss_value(dss.Solution.Converged, False)),
                            "mode": _dss_value(dss.Solution.Mode),
                            "frequency_hz": _dss_value(dss.Solution.Frequency),
                            "iterations": _dss_value(dss.Solution.Iterations),
                            "hour": _dss_value(dss.Solution.Hour),
                            "step": _dss_value(dss.Solution.Number),
                        },
                        "circuit": {
                            "total_power_kw_kvar": total_power,
                            "losses_w_var": losses,
                            "bus_voltage_pu_min": min(pu_voltages) if pu_voltages else None,
                            "bus_voltage_pu_max": max(pu_voltages) if pu_voltages else None,
                        },
                    },
                }
        except ModelConversionError:
            raise
        except Exception as exc:
            raise ModelConversionError(f"Failed to inspect OpenDSS model: {exc}") from exc
        finally:
            try:
                dss.Basic.ClearAll()
            except Exception:
                pass
            os.chdir(previous_cwd)


def _list_files(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(root)),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def _artifact_has_profiles(artifact: dict[str, Any]) -> bool:
    for item in artifact.get("files", []):
        path = str(item.get("path", "")).lower()
        filename = Path(path).name
        if path.startswith("profiles/") or "loadshape" in filename or filename.endswith(
            (".csv", ".dbl", ".txt")
        ):
            return True
    return False


def _sensor_ids_from_inspection(inspection: dict[str, Any]) -> set[str]:
    sensor_ids: set[str] = set()
    for bus in inspection.get("buses", []):
        name = bus.get("name")
        if not isinstance(name, str):
            continue
        for node in bus.get("nodes", []):
            # LocalFeeder/OpenDSS publishes node IDs in uppercase.  Keep the
            # canonical sensor artifact aligned with that runtime spelling.
            sensor_ids.add(f"{name}.{node}".upper())
    return sensor_ids


def _empty_sensor_config() -> dict[str, list[str]]:
    return {sensor_type: [] for sensor_type in SENSOR_TYPES}


def _normalize_sensor_config(payload: dict[str, Any], valid_ids: set[str]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    valid_ids_by_lower = {value.lower(): value for value in valid_ids}
    for sensor_type in SENSOR_TYPES:
        values = payload.get(sensor_type, [])
        if not isinstance(values, list):
            raise ModelManagerError(f"Sensor field '{sensor_type}' must be a list")
        unique_values = []
        for value in values:
            canonical_value = valid_ids_by_lower.get(value.lower()) if isinstance(value, str) else None
            if canonical_value is None:
                raise ModelManagerError(
                    f"Unknown sensor location '{value}' for sensor type '{sensor_type}'"
                )
            if canonical_value not in unique_values:
                unique_values.append(canonical_value)
        normalized[sensor_type] = unique_values
    return normalized


def _sensor_artifact_files(sensor_directory: Path) -> dict[str, str]:
    return {
        "voltage": "voltage_ids.json",
        "real_power": "real_ids.json",
        "reactive_power": "reactive_ids.json",
    }


def save_sensor_config(
    models_root: Path | str,
    user: str,
    model_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    root = _model_root(models_root, user, model_id)
    inspection = load_inspection(models_root, user, model_id)
    normalized = _normalize_sensor_config(payload, _sensor_ids_from_inspection(inspection))
    _atomic_write(root / "sensor_config.json", normalized)
    sensor_directory = root / "artifacts" / "sensors"
    sensor_directory.mkdir(parents=True, exist_ok=True)
    for sensor_type, filename in _sensor_artifact_files(sensor_directory).items():
        _atomic_write(sensor_directory / filename, normalized[sensor_type])
    _atomic_write(
        sensor_directory / "sensors.json",
        sorted({sensor_id for values in normalized.values() for sensor_id in values}),
    )
    record = load_model_record(models_root, user, model_id)
    record["sensors"] = {
        "counts": {sensor_type: len(values) for sensor_type, values in normalized.items()},
        "files": _list_files(sensor_directory),
    }
    record["updated_at"] = _now()
    _atomic_write(root / "model.json", record)
    inspection["sensors"] = normalized
    _atomic_write(root / "inspection.json", inspection)
    return normalized


def load_sensor_config(models_root: Path | str, user: str, model_id: str) -> dict[str, list[str]]:
    root = _model_root(models_root, user, model_id)
    config_path = root / "sensor_config.json"
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            return _normalize_sensor_config(config, _sensor_ids_from_inspection(load_inspection(models_root, user, model_id)))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelManagerError(f"Model '{model_id}' sensor configuration is unreadable") from exc
    return _empty_sensor_config()


def upload_sensor_file(
    models_root: Path | str,
    user: str,
    model_id: str,
    content: bytes,
    sensor_type: str,
) -> dict[str, list[str]]:
    """Import a legacy list-style sensor JSON into one sensor category."""

    if sensor_type not in SENSOR_TYPES:
        raise ModelManagerError(
            f"Unsupported sensor type '{sensor_type}'. Choose one of: {', '.join(SENSOR_TYPES)}."
        )
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelManagerError("Sensor file must contain valid JSON") from exc
    if isinstance(payload, dict):
        config = load_sensor_config(models_root, user, model_id)
        for key, values in payload.items():
            if key in SENSOR_TYPES:
                config[key] = values
        return save_sensor_config(models_root, user, model_id, config)
    if not isinstance(payload, list):
        raise ModelManagerError("Sensor file must be a JSON list of bus.phase IDs or a sensor config object")
    config = load_sensor_config(models_root, user, model_id)
    config[sensor_type] = payload
    return save_sensor_config(models_root, user, model_id, config)


def _find_master(root: Path) -> Path:
    masters = [
        path for path in root.rglob("*.dss")
        if path.name.lower() in {"master.dss", "ieee123master.dss"}
    ]
    if not masters:
        raise ModelConversionError("Ditto did not produce a Master.dss OpenDSS entrypoint.")
    return sorted(masters, key=lambda path: (len(path.relative_to(root).parts), str(path)))[0]


def _normalize_opendss_master(master: Path) -> None:
    """Normalize Vsource bus references for the LocalFeeder runtime.

    OpenDSS accepts ``sourcebus.1.2.3`` as a Vsource bus reference, but the
    LocalFeeder component reads the source bus name and appends phase numbers
    itself.  Keeping the base bus in the generated master preserves the same
    circuit while avoiding ``sourcebus.1.2.3.1`` node lookups.
    """

    text = master.read_text(encoding="utf-8")
    lines = []
    changed = False
    bus_pattern = re.compile(r"(\bbus1\s*=\s*)([^\s]+)", re.IGNORECASE)
    phases_pattern = re.compile(r"\bphases\s*=\s*(\d+)", re.IGNORECASE)
    for line in text.splitlines(keepends=True):
        lowered = line.lower()
        if "new circuit" in lowered or "new vsource" in lowered:
            phases_match = phases_pattern.search(line)
            bus_match = bus_pattern.search(line)
            if phases_match and bus_match:
                bus_name = bus_match.group(2)
                parts = bus_name.split(".")
                while len(parts) > 1 and parts[-1].isdigit():
                    parts.pop()
                normalized_bus = ".".join(parts)
                if normalized_bus != bus_name:
                    line = line[: bus_match.start(2)] + normalized_bus + line[bus_match.end(2) :]
                    changed = True
        lines.append(line)
    if changed:
        master.write_text("".join(lines), encoding="utf-8")


def _read_coordinate_sidecar(source_directory: Path) -> dict[str, tuple[float, float]]:
    coordinates: dict[str, tuple[float, float]] = {}
    candidates = [
        path
        for path in source_directory.rglob("*")
        if path.is_file() and "buscoord" in path.name.lower()
    ]
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("!") or stripped.startswith("#"):
                continue
            tokens = re.split(r"[\s,]+", stripped)
            if tokens and tokens[0].lower() in {"setbusxy", "bus"}:
                tokens = tokens[1:]
            if len(tokens) < 3:
                continue
            try:
                coordinates[tokens[0].lower()] = (float(tokens[1]), float(tokens[2]))
            except ValueError:
                continue
    return coordinates


def _apply_coordinate_sidecar(
    source_directory: Path,
    artifact_directory: Path,
    valid_bus_names: set[str] | None = None,
) -> None:
    """Carry OpenDSS BusCoords.dat/CSV data into the generated DSS artifact."""

    coordinates = _read_coordinate_sidecar(source_directory)
    if valid_bus_names:
        coordinates = {
            name: coordinate
            for name, coordinate in coordinates.items()
            if name.lower() in {value.lower() for value in valid_bus_names}
        }
    if not coordinates:
        return
    coordinate_files = [
        path for path in artifact_directory.rglob("*")
        if path.is_file() and path.name.lower() == "buscoords.dss"
    ]
    coordinate_file = coordinate_files[0] if coordinate_files else artifact_directory / "BusCoords.dss"
    if not coordinate_file.exists():
        coordinate_file.write_text("", encoding="utf-8")
    original_text = coordinate_file.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(r"(setbusxy\s+)([^\s]+)(\s+)([^\s]+)(\s+)([^\s]+)", re.IGNORECASE)
    if not pattern.search(original_text):
        coordinate_file.write_text(
            "".join(f"SetBusXY {bus} {x} {y}\n" for bus, (x, y) in coordinates.items()),
            encoding="utf-8",
        )
    lines = []
    for line in coordinate_file.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True):
        match = pattern.search(line)
        if not match:
            lines.append(line)
            continue
        bus_name = match.group(2)
        coordinate = coordinates.get(bus_name.lower())
        if coordinate is None:
            lines.append(line)
            continue
        replacement = f"{match.group(1)}{bus_name}{match.group(3)}{coordinate[0]}{match.group(5)}{coordinate[1]}"
        lines.append(line[: match.start()] + replacement + line[match.end() :])
    coordinate_file.write_text("".join(lines), encoding="utf-8")

    source_master_candidates = [
        path for path in artifact_directory.rglob("*.dss")
        if path.name.lower() in {"master.dss", "ieee123master.dss"}
    ]
    if not source_master_candidates:
        return
    master = sorted(source_master_candidates, key=lambda path: len(path.relative_to(artifact_directory).parts))[0]
    master_text = master.read_text(encoding="utf-8", errors="ignore")
    if "buscoords" not in master_text.lower():
        relative_coordinate_file = coordinate_file.relative_to(master.parent)
        master.write_text(
            master_text.rstrip() + f"\nRedirect {relative_coordinate_file.as_posix()}\n",
            encoding="utf-8",
        )


def _extract_upload(content: bytes, filename: str, source_dir: Path) -> None:
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_FILES:
                raise ModelManagerError("Archive contains too many files")
            total_size = sum(info.file_size for info in infos)
            if total_size > MAX_ARCHIVE_UNCOMPRESSED_SIZE:
                raise ModelManagerError("Archive expands beyond the 2 GB safety limit")
            for info in infos:
                member = Path(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    raise ModelManagerError("Archive contains an unsafe path")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ModelManagerError("Archive symlinks are not supported")
                target = source_dir / member
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        return
    if filename.lower().endswith(".zip"):
        raise ModelManagerError("Uploaded file is not a valid ZIP archive")
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise ModelManagerError("Uploaded file has no usable filename")
    (source_dir / safe_name).write_bytes(content)


def _copy_opendss_source(source_dir: Path, artifact_dir: Path) -> None:
    """Preserve an existing OpenDSS case instead of rewriting it through Ditto."""

    artifact_dir.mkdir(parents=True, exist_ok=True)
    for path in source_dir.rglob("*"):
        if not path.is_file() or "__macosx" in path.parts:
            continue
        relative = path.relative_to(source_dir)
        destination = artifact_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _cleanup_opendss_exports(directory: Path, before: set[Path]) -> None:
    """Remove process-relative OpenDSS export files created during conversion."""

    gc.collect()
    for path in directory.glob("*_EXP_*.csv"):
        if path not in before:
            path.unlink(missing_ok=True)


def _atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def stage_model_upload(
    content: bytes,
    original_filename: str,
    models_root: Path | str,
    user: str,
    *,
    name: str = "",
    description: str = "",
    requested_format: str = "auto",
    load_model_id: str | None = None,
    crs: str | None = None,
) -> dict[str, Any]:
    _validate_user(user)
    root = Path(models_root) / user / uuid4().hex
    source_dir = root / "source"
    artifact_dir = root / "artifacts" / "opendss"
    source_dir.mkdir(parents=True, exist_ok=False)
    working_directory = Path.cwd()
    existing_opendss_exports = set(working_directory.glob("*_EXP_*.csv"))
    try:
        _extract_upload(content, original_filename, source_dir)
        detected = detect_model_format(source_dir, requested_format)
        with redirect_stdout(io.StringIO()):
            system, reader, reader_name = _load_system(detected, crs, load_model_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        writer_warnings: list[str] = []
        if detected.format == "opendss":
            # Existing OpenDSS cases are already in the target format. Keep
            # their redirects, LoadShapes.dss, CSV profiles, and sidecars
            # intact instead of losing them in an OpenDSS -> GDM -> OpenDSS
            # round trip.
            _copy_opendss_source(source_dir, artifact_dir)
        else:
            try:
                from ditto.writers.opendss.write import Writer
                from loguru import logger

                warning_stream = io.StringIO()
                warning_sink = logger.add(warning_stream, level="WARNING", format="{message}")
                try:
                    with redirect_stdout(io.StringIO()):
                        Writer(system).write(
                            output_path=artifact_dir,
                            separate_substations=False,
                            separate_feeders=False,
                        )
                finally:
                    logger.remove(warning_sink)
                writer_warnings = [
                    line.strip()
                    for line in warning_stream.getvalue().splitlines()
                    if line.strip()
                ]
            except Exception as exc:
                raise ModelConversionError(f"Failed to write OpenDSS artifact: {exc}") from exc

        master = _find_master(artifact_dir)
        _normalize_opendss_master(master)
        valid_bus_names = {
            str(getattr(component, "name", ""))
            for component in system.iter_all_components()
            if type(component).__name__ == "DistributionBus"
        }
        _apply_coordinate_sidecar(source_dir, artifact_dir, valid_bus_names)
        inspection = inspect_opendss_model(master)
        warnings = list(dict.fromkeys(_reader_warnings(reader) + writer_warnings))
        source_files = _list_files(source_dir)
        artifact_files = _list_files(artifact_dir)
        artifact_metadata = {
            "format": "opendss",
            "entrypoint": str(master.relative_to(artifact_dir)),
            "files": artifact_files,
        }
        artifact_metadata["profiles_available"] = _artifact_has_profiles(artifact_metadata)
        conversion = {
            "format": detected.format,
            "reader": reader_name,
            "entrypoint": detected.entrypoint_name(),
            "source_files": [item["path"] for item in source_files],
            "load_model_ids": detected.load_model_ids,
            "warnings": warnings,
            "reason": detected.reason,
            "requested_format": requested_format,
            "original_filename": original_filename,
            "artifact_format": "opendss",
            "artifact_entrypoint": str(master.relative_to(artifact_dir)),
        }
        model_id = root.name
        record = {
            "id": model_id,
            "name": name.strip() or Path(original_filename).stem or model_id,
            "description": description.strip(),
            "domain": "distribution",
            "source_format": detected.format,
            "status": "ready_with_warnings" if warnings else "ready",
            "created_at": _now(),
            "updated_at": _now(),
            "source": {
                "original_filename": original_filename,
                "files": source_files,
                "sha256": hashlib.sha256(content).hexdigest(),
            },
            "conversion": conversion,
            "artifacts": {
                "opendss": artifact_metadata
            },
            "inspection_summary": inspection["summary"],
        }
        _atomic_write(root / "model.json", record)
        _atomic_write(root / "inspection.json", inspection)
        _atomic_write(root / "sensor_config.json", _empty_sensor_config())
        sensor_directory = root / "artifacts" / "sensors"
        sensor_directory.mkdir(parents=True, exist_ok=True)
        for sensor_type, filename in _sensor_artifact_files(sensor_directory).items():
            _atomic_write(sensor_directory / filename, [])
        _atomic_write(sensor_directory / "sensors.json", [])
        record["sensors"] = {
            "counts": {sensor_type: 0 for sensor_type in SENSOR_TYPES},
            "files": _list_files(sensor_directory),
        }
        _atomic_write(root / "model.json", record)
        return record
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    finally:
        _cleanup_opendss_exports(working_directory, existing_opendss_exports)


def _model_root(models_root: Path | str, user: str, model_id: str) -> Path:
    _validate_user(user)
    _validate_id(model_id)
    root = Path(models_root) / user / model_id
    if not root.is_dir() or not (root / "model.json").is_file():
        raise ModelNotFoundError(f"Model '{model_id}' was not found")
    return root


def load_model_record(models_root: Path | str, user: str, model_id: str) -> dict[str, Any]:
    root = _model_root(models_root, user, model_id)
    try:
        return json.loads((root / "model.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelManagerError(f"Model '{model_id}' metadata is unreadable") from exc


def list_model_records(models_root: Path | str, user: str) -> list[dict[str, Any]]:
    _validate_user(user)
    root = Path(models_root) / user
    if not root.is_dir():
        return []
    records = []
    for model_dir in root.iterdir():
        if not model_dir.is_dir() or not (model_dir / "model.json").is_file():
            continue
        try:
            records.append(json.loads((model_dir / "model.json").read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(records, key=lambda record: record.get("created_at", ""), reverse=True)


def update_model_record(
    models_root: Path | str,
    user: str,
    model_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    root = _model_root(models_root, user, model_id)
    record = load_model_record(models_root, user, model_id)
    if name is not None:
        if not name.strip():
            raise ModelManagerError("Model name cannot be empty")
        record["name"] = name.strip()
    if description is not None:
        record["description"] = description.strip()
    record["updated_at"] = _now()
    _atomic_write(root / "model.json", record)
    return record


def delete_model(models_root: Path | str, user: str, model_id: str) -> None:
    root = _model_root(models_root, user, model_id)
    shutil.rmtree(root)


def load_inspection(models_root: Path | str, user: str, model_id: str) -> dict[str, Any]:
    root = _model_root(models_root, user, model_id)
    try:
        inspection = json.loads((root / "inspection.json").read_text(encoding="utf-8"))
        has_coordinate_sidecar = bool(_read_coordinate_sidecar(root / "source"))
        has_geo_features = bool(inspection.get("geojson", {}).get("features"))
        if (
            inspection.get("source_of_truth") == "opendss"
            and "geojson" in inspection
            and "coordinate_mode" in inspection
            and (has_geo_features or not has_coordinate_sidecar)
        ):
            sensor_path = root / "sensor_config.json"
            if sensor_path.is_file():
                inspection["sensors"] = json.loads(sensor_path.read_text(encoding="utf-8"))
            return inspection
        # Migrate inspection files created by the first model-manager slice.
        # The generated DSS artifact is now authoritative for the UI.
        refreshed = inspect_opendss_model(opendss_entrypoint(models_root, user, model_id))
        sensor_path = root / "sensor_config.json"
        if sensor_path.is_file():
            refreshed["sensors"] = json.loads(sensor_path.read_text(encoding="utf-8"))
        _atomic_write(root / "inspection.json", refreshed)
        record = load_model_record(models_root, user, model_id)
        record["inspection_summary"] = refreshed["summary"]
        _atomic_write(root / "model.json", record)
        return refreshed
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelManagerError(f"Model '{model_id}' inspection is unavailable") from exc


def opendss_entrypoint(models_root: Path | str, user: str, model_id: str) -> Path:
    root = _model_root(models_root, user, model_id)
    record = load_model_record(models_root, user, model_id)
    entrypoint = record.get("artifacts", {}).get("opendss", {}).get("entrypoint")
    if not isinstance(entrypoint, str):
        raise ModelConversionError(f"Model '{model_id}' has no OpenDSS artifact")
    artifact_root = root / "artifacts" / "opendss"
    resolved = (artifact_root / entrypoint).resolve()
    if artifact_root.resolve() not in resolved.parents or not resolved.is_file():
        raise ModelConversionError(f"Model '{model_id}' has an invalid OpenDSS entrypoint")
    _normalize_opendss_master(resolved)
    _apply_coordinate_sidecar(root / "source", artifact_root)
    return resolved


def copy_model_to_component_run(
    models_root: Path | str,
    user: str,
    model_id: str,
    build_dir: Path,
    component_name: str,
) -> str:
    """Copy the OpenDSS artifact into a LocalFeeder component working directory."""

    entrypoint = opendss_entrypoint(models_root, user, model_id)
    model_root = _model_root(models_root, user, model_id)
    artifact_root = model_root / "artifacts" / "opendss"
    safe_component_name = Path(component_name).name
    if safe_component_name != component_name or safe_component_name in {"", ".", ".."}:
        raise ModelManagerError("Component names cannot contain path traversal")
    component_dir = build_dir / safe_component_name
    destination = component_dir / "opendss"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(artifact_root, destination, dirs_exist_ok=True)
    generated_profiles = artifact_root / "profiles"
    if generated_profiles.is_dir():
        shutil.copytree(generated_profiles, component_dir / "profiles", dirs_exist_ok=True)
    relative_entrypoint = entrypoint.relative_to(artifact_root)
    return str(Path("opendss") / relative_entrypoint)


def copy_model_sensors_to_component_run(
    models_root: Path | str,
    user: str,
    model_id: str,
    build_dir: Path,
    component_name: str,
) -> None:
    root = _model_root(models_root, user, model_id)
    sensor_directory = root / "artifacts" / "sensors"
    destination = build_dir / component_name / "sensors"
    destination.mkdir(parents=True, exist_ok=True)
    if sensor_directory.is_dir():
        for path in sensor_directory.iterdir():
            if path.is_file():
                shutil.copy2(path, destination / path.name)


def resolve_model_references(
    wiring: dict[str, Any],
    models_root: Path | str,
    user: str,
    build_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Resolve managed model IDs for supported simulation components.

    The submitted wiring remains model-ID based.  The returned wiring is the
    private runner copy with the generated OpenDSS entrypoint materialized.
    """

    resolved = copy.deepcopy(wiring)
    references: list[dict[str, Any]] = []
    for component in resolved.get("components", []):
        parameters = component.get("parameters")
        if not isinstance(parameters, dict):
            continue
        model_id = parameters.get("model_id")
        if not model_id:
            continue
        component_type = component.get("type")
        if component_type not in {"Feeder", "LocalFeeder"}:
            raise ModelManagerError(
                f"Managed models are not supported by component type '{component_type}' yet."
            )
        if not isinstance(model_id, str):
            raise ModelManagerError("Feeder model_id must be a string")
        record = load_model_record(models_root, user, model_id)
        if record.get("status") not in {"ready", "ready_with_warnings"}:
            raise ModelManagerError(
                f"Model '{model_id}' is not ready for simulation (status: {record.get('status')})."
            )
        component_name = component.get("name")
        if not isinstance(component_name, str) or not component_name:
            raise ModelManagerError("Feeder components must have a name before using a managed model")
        entrypoint = copy_model_to_component_run(
            models_root, user, model_id, build_dir, component_name
        )
        copy_model_sensors_to_component_run(
            models_root, user, model_id, build_dir, component_name
        )
        parameters.pop("model_id", None)
        parameters["user_uploads_model"] = True
        parameters["existing_feeder_file"] = entrypoint
        parameters["opendss_location"] = "opendss"
        opendss_artifact = record.get("artifacts", {}).get("opendss", {})
        profiles_available = opendss_artifact.get("profiles_available")
        if profiles_available is None:
            profiles_available = _artifact_has_profiles(opendss_artifact)
        parameters["profile_location"] = "profiles" if profiles_available else ""
        parameters["sensor_location"] = "sensors/sensors.json"
        references.append(
            {
                "model_id": model_id,
                "model_name": record.get("name", model_id),
                "source_format": record.get("source_format"),
                "status": record.get("status"),
                "artifact_format": "opendss",
                "artifact_entrypoint": entrypoint,
            }
        )
        sensor_directory = build_dir / component_name / "sensors"
        for sensor_component in resolved.get("components", []):
            sensor_parameters = sensor_component.get("parameters")
            if not isinstance(sensor_parameters, dict):
                continue
            if sensor_component.get("type") != "MeasurementComponent":
                continue
            sensor_name = str(
                sensor_parameters.get("name") or sensor_component.get("name") or ""
            ).lower()
            if "voltage" in sensor_name:
                sensor_file = "voltage_ids.json"
            elif "power_real" in sensor_name:
                sensor_file = "real_ids.json"
            elif "power_imaginary" in sensor_name or "reactive" in sensor_name:
                sensor_file = "reactive_ids.json"
            else:
                continue
            if (sensor_directory / sensor_file).is_file():
                sensor_parameters["measurement_file"] = f"../{component_name}/sensors/{sensor_file}"
    return resolved, references


def archive_directory(directory: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(directory))
    return output


def source_directory(models_root: Path | str, user: str, model_id: str) -> Path:
    return _model_root(models_root, user, model_id) / "source"


def artifact_directory(models_root: Path | str, user: str, model_id: str) -> Path:
    return _model_root(models_root, user, model_id) / "artifacts" / "opendss"
