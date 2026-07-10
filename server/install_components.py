"""Sync OEDISI components into the frontend catalog and install them.

Usage:
    uv run python install_components.py               # sync catalog, then install
    uv run python install_components.py --sync-only
    uv run python install_components.py --install-only
    uv run python install_components.py --yes         # accept all prompts

Sync reads component_definition.json/schema.json from $OEDISI_COMPONENTS,
copies them into src/lib/definitions and src/lib/schemas (prompting before
overwriting local files that differ — some are intentionally hand-edited),
registers new components in server/components.json, and regenerates
src/lib/catalog.json from the local files.
"""

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_DIR.parent
DEFINITIONS_DIR = PROJECT_ROOT / "src" / "lib" / "definitions"
SCHEMAS_DIR = PROJECT_ROOT / "src" / "lib" / "schemas"
CATALOG_PATH = PROJECT_ROOT / "src" / "lib" / "catalog.json"
COMPONENTS_JSON_PATH = SERVER_DIR / "components.json"

# Bootstrap metadata for components that predate catalog.json. Once a component
# is in catalog.json + components.json, those files are the source of truth.
KNOWN_COMPONENTS: dict[str, dict[str, str]] = {
    "LocalFeeder": {
        "id": "Feeder",
        "base_name": "feeder",
        "name": "Feeder",
        "description": "OpenDSS simulation engine",
    },
    "wls_federate": {
        "id": "StateEstimatorComponent",
        "name": "State Estimator",
        "description": "WLS state estimator",
    },
    "lindistflow_federate": {
        "id": "LinDistFlowComponent",
        "base_name": "lin_dist_flow_algorithm",
        "name": "LinDistFlow Algorithm",
        "description": "LinDistFlow optimization algorithm",
    },
    "measuring_federate": {
        "id": "MeasurementComponent",
        "base_name": "sensor",
        "schema_file": "measuring_federate.json",
        "name": "Sensor",
        "description": "Sensor model",
    },
    "recorder": {
        "id": "Recorder",
        "name": "Recorder",
        "description": "Records simulation results",
    },
    "omoo_federate": {
        "id": "OMOOComponent",
        "name": "OMOO",
        "description": "Optimal Power Flow",
    },
    "nlpdopf": {
        "id": "NlpDopfComponent",
        "name": "NLP DOPF",
        "description": "Optimal Power Flow",
    },
    "nlpdsse": {
        "id": "NlpDsseComponent",
        "name": "NLP DSSE",
        "description": "NLP State Estimator",
    },
    "pnnl-dopf-admm": {
        "id": "PnnlDopfAdmmComponent",
        "name": "ADMM DOPF",
        "description": "Optimal Power Flow (requires Hub)",
    },
    "pnnl-hub-control": {
        "id": "PnnlHubControlComponent",
        "name": "DOPF Hub Control",
        "description": "Hub for controlling multiple DOPF",
    },
    "pnnl-hub-power": {
        "id": "PnnlHubPowerComponent",
        "name": "DOPF Hub Power",
        "description": "Hub for splitting power",
    },
    "pnnl-hub-voltage": {
        "id": "PnnlHubVoltageComponent",
        "name": "DOPF Hub Voltage",
        "description": "Hub for splitting voltage",
    },
    "ornl-ev-pso": {
        "id": "EVCSComponent",
        "name": "ORNL EV Scheduler",
        "description": "PSO-based EV charging optimization",
    },
    "ornl-dopf-pso": {
        "id": "DOPFPSOComponent",
        "name": "ORNL DOPF (PSO)",
        "description": "Distribution OPF via Particle Swarm Optimization",
    },
    "ornl-dsse-gnwls": {
        "id": "DSSEGNWLSComponent",
        "name": "ORNL DSSE (GN-WLS)",
        "description": "Distribution state estimation via Gauss-Newton WLS",
    },
    "pnnl-dsse-ekf": {
        "id": "PnnlDsseEkfComponent",
        "name": "PNNL DSSE EKF",
        "description": "PNNL DSSE EKF component",
    },
}

UPPERCASE_WORDS = {"pnnl", "ornl", "ev", "dopf", "pso", "dsse", "wls", "nlp", "admm", "emt", "swod", "omoo"}

SKIP_DIRS = {".git", "node_modules", "broker"}


def confirm(question: str, default: bool, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        return default
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def prompt_text(question: str, default: str, assume_yes: bool) -> str:
    if assume_yes or not sys.stdin.isatty():
        return default
    answer = input(f"{question} [{default}]: ").strip()
    return answer or default


def generate_component_id(base_name: str) -> str:
    pascal = "".join(word.capitalize() for word in base_name.replace("-", "_").split("_"))
    return pascal if pascal.endswith("Component") else f"{pascal}Component"


def generate_display_name(folder_name: str) -> str:
    words = folder_name.replace("-", "_").split("_")
    return " ".join(w.upper() if w.lower() in UPPERCASE_WORDS else w.capitalize() for w in words)


def find_file(root: Path, file_name: str) -> Path | None:
    direct = root / file_name
    if direct.exists():
        return direct
    for path in sorted(root.rglob(file_name)):
        if not SKIP_DIRS.intersection(path.parts):
            return path
    return None


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def show_diff(local, upstream, label: str) -> None:
    local_lines = json.dumps(local, indent=2, sort_keys=True).splitlines()
    upstream_lines = json.dumps(upstream, indent=2, sort_keys=True).splitlines()
    diff = list(difflib.unified_diff(local_lines, upstream_lines,
                                     fromfile=f"local/{label}", tofile=f"upstream/{label}", lineterm=""))
    for line in diff[:60]:
        print(f"    {line}")
    if len(diff) > 60:
        print(f"    ... ({len(diff) - 60} more lines)")


def sync_file(source: Path, dest: Path, label: str, assume_yes: bool) -> None:
    """Copy source to dest, prompting before overwriting a differing local file."""
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        print(f"  Copied new file {dest.relative_to(PROJECT_ROOT)}")
        return
    local = load_json(dest)
    upstream = load_json(source)
    if local == upstream:
        return
    print(f"  {label} differs from upstream:")
    show_diff(local, upstream, label)
    if confirm(f"  Overwrite local {label} with upstream version?", default=False, assume_yes=assume_yes):
        shutil.copyfile(source, dest)
        print(f"  Updated {dest.relative_to(PROJECT_ROOT)}")
    else:
        print(f"  Kept local {dest.relative_to(PROJECT_ROOT)}")


def resolve_components_root() -> Path:
    components_root = os.environ.get("OEDISI_COMPONENTS")
    if not components_root:
        print("\nError: The OEDISI_COMPONENTS environment variable is not set.", file=sys.stderr)
        print("Please set it to the path of your local OEDISI Components directory.", file=sys.stderr)
        print("Example: export OEDISI_COMPONENTS=\"$HOME/dev/oedisi-components/Components\"\n", file=sys.stderr)
        sys.exit(1)
    path = Path(components_root).resolve()
    if not path.exists():
        print(f"Error: OEDISI_COMPONENTS directory not found at: {path}", file=sys.stderr)
        sys.exit(1)
    return path


def load_components_mapping() -> dict[str, str]:
    if not COMPONENTS_JSON_PATH.exists():
        print(f"Error: components.json not found at: {COMPONENTS_JSON_PATH}", file=sys.stderr)
        sys.exit(1)
    try:
        return load_json(COMPONENTS_JSON_PATH)
    except json.JSONDecodeError as exc:
        print(f"Error parsing components.json: {exc}", file=sys.stderr)
        sys.exit(1)


def folder_of_mapping_path(raw_path: str) -> str | None:
    """Extract the component folder name from a ${OEDISI_COMPONENTS}/... path."""
    prefix = "${OEDISI_COMPONENTS}/"
    if not raw_path.startswith(prefix):
        return None
    return raw_path[len(prefix):].split("/")[0]


def sync_catalog(components_root: Path, assume_yes: bool) -> None:
    mapping = load_components_mapping()
    catalog: list[dict] = load_json(CATALOG_PATH) if CATALOG_PATH.exists() else []
    catalog_by_id = {entry["id"]: entry for entry in catalog}

    # components.json can map several ids to one folder (e.g. Feeder/LocalFeeder)
    folder_to_ids: dict[str, list[str]] = {}
    for comp_id, raw_path in mapping.items():
        folder = folder_of_mapping_path(raw_path)
        if folder is not None:
            folder_to_ids.setdefault(folder, []).append(comp_id)

    seen_ids: set[str] = set()
    new_entries: list[dict] = []
    mapping_changed = False

    for folder_dir in sorted(components_root.iterdir()):
        folder = folder_dir.name
        if not folder_dir.is_dir() or folder in SKIP_DIRS or folder.startswith("."):
            continue

        known = KNOWN_COMPONENTS.get(folder, {})
        mapped_ids = folder_to_ids.get(folder, [])
        comp_id = (next((i for i in mapped_ids if i in catalog_by_id), None)
                   or known.get("id")
                   or (mapped_ids[0] if mapped_ids else None))

        # An existing components.json path wins over discovery, so hand-picked
        # nested definition paths (e.g. nlpdopf) are preserved.
        definition_path = None
        if comp_id and comp_id in mapping:
            candidate = Path(mapping[comp_id].replace("${OEDISI_COMPONENTS}", str(components_root)))
            if candidate.exists():
                definition_path = candidate
        if definition_path is None:
            definition_path = find_file(folder_dir, "component_definition.json")
        if definition_path is None:
            print(f"Skipping '{folder}': no component_definition.json found.")
            continue

        entry = catalog_by_id.get(comp_id) if comp_id else None
        if entry is None:
            default_name = known.get("name") or generate_display_name(folder)
            default_description = known.get("description") or f"{default_name} component"
            print(f"\nNew component found: {folder}")
            if not confirm(f"Add '{folder}' to the catalog?", default=True, assume_yes=assume_yes):
                continue
            base_name = known.get("base_name") or folder.replace("-", "_")
            comp_id = comp_id or generate_component_id(base_name)
            entry = {
                "id": comp_id,
                "name": prompt_text("  Display name", default_name, assume_yes),
                "description": prompt_text("  Description", default_description, assume_yes),
                "definitionFile": f"{base_name}.json",
            }
            new_entries.append(entry)
        seen_ids.add(entry["id"])

        base_name = Path(entry["definitionFile"]).stem
        schema_file = known.get("schema_file", f"{base_name}.json")

        print(f"Syncing {folder} -> {entry['id']}")
        sync_file(definition_path, DEFINITIONS_DIR / entry["definitionFile"],
                  f"definitions/{entry['definitionFile']}", assume_yes)

        schema_path = definition_path.parent / "schema.json"
        if not schema_path.exists():
            schema_path = find_file(folder_dir, "schema.json")
        if schema_path is not None:
            sync_file(schema_path, SCHEMAS_DIR / schema_file, f"schemas/{schema_file}", assume_yes)
        elif not (SCHEMAS_DIR / schema_file).exists():
            print(f"  Warning: no schema.json for '{folder}'; catalog entry will have no inputSchema.")

        if entry["id"] not in mapping:
            rel = definition_path.relative_to(components_root)
            mapping[entry["id"]] = f"${{OEDISI_COMPONENTS}}/{rel.as_posix()}"
            mapping_changed = True
            print(f"  Registered '{entry['id']}' in server/components.json")

    for entry in catalog:
        if entry["id"] not in seen_ids:
            print(f"Warning: catalog entry '{entry['id']}' has no folder under {components_root}; keeping local files.")

    # Rebuild the catalog from local files: existing order first, new entries appended.
    output = []
    for entry in catalog + new_entries:
        definition_file = DEFINITIONS_DIR / entry["definitionFile"]
        if not definition_file.exists():
            print(f"Warning: missing {definition_file.relative_to(PROJECT_ROOT)}; dropping '{entry['id']}' from catalog.")
            continue
        known = next((k for k in KNOWN_COMPONENTS.values() if k.get("id") == entry["id"]), {})
        schema_file = SCHEMAS_DIR / known.get("schema_file", entry["definitionFile"])
        result = {
            "id": entry["id"],
            "name": entry["name"],
            "description": entry["description"],
            "definitionFile": entry["definitionFile"],
            "definition": load_json(definition_file),
        }
        if schema_file.exists():
            result["inputSchema"] = load_json(schema_file)
        output.append(result)

    if not CATALOG_PATH.exists() or load_json(CATALOG_PATH) != output:
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            f.write("\n")
        print(f"\nWrote {CATALOG_PATH.relative_to(PROJECT_ROOT)} ({len(output)} components)")
    else:
        print(f"\n{CATALOG_PATH.relative_to(PROJECT_ROOT)} is up to date ({len(output)} components)")

    if mapping_changed:
        with open(COMPONENTS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=4)
            f.write("\n")
        print("Updated server/components.json")


def install_components(components_root: Path) -> None:
    mapping = load_components_mapping()

    component_dirs = []
    broker_dir = components_root / "broker"
    if broker_dir.exists():
        component_dirs.append(broker_dir)

    for name, raw_path in mapping.items():
        if "${OEDISI_COMPONENTS}" in raw_path:
            comp_def_path = Path(raw_path.replace("${OEDISI_COMPONENTS}", str(components_root))).resolve()
            if comp_def_path.exists():
                comp_dir = comp_def_path.parent
                # Check for standard component structure (pyproject.toml or setup.py directly in the component folder)
                if (comp_dir / "pyproject.toml").exists() or (comp_dir / "setup.py").exists():
                    if comp_dir not in component_dirs:
                        component_dirs.append(comp_dir)
                else:
                    print(f"Warning: Component '{name}' does not follow standard structure guidance (missing pyproject.toml/setup.py in {comp_dir}). Skipping.", file=sys.stderr)
            else:
                print(f"Warning: Component path for {name} does not exist: {comp_def_path}", file=sys.stderr)

    print(f"Installing {len(component_dirs)} components into virtual environment...")
    failed_components = []
    for comp_dir in component_dirs:
        print(f"  Installing {comp_dir.name} ({comp_dir})...")
        try:
            subprocess.run(
                ["uv", "pip", "install", "-e", str(comp_dir)],
                cwd=SERVER_DIR,
                check=True
            )
        except subprocess.CalledProcessError as exc:
            print(f"Warning: Failed to install component {comp_dir.name} ({exc}). Skipping.", file=sys.stderr)
            failed_components.append(comp_dir.name)

    if failed_components:
        print(f"\nCompleted with warnings. The following components failed to install: {', '.join(failed_components)}")
    else:
        print("\nAll components installed successfully!")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sync-only", action="store_true", help="sync catalog/schemas without installing")
    group.add_argument("--install-only", action="store_true", help="install packages without syncing the catalog")
    parser.add_argument("-y", "--yes", action="store_true", help="accept all prompts (adds new components, overwrites changed files)")
    args = parser.parse_args()

    components_root = resolve_components_root()
    if not args.install_only:
        sync_catalog(components_root, assume_yes=args.yes)
    if not args.sync_only:
        install_components(components_root)


if __name__ == "__main__":
    main()
