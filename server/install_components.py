import os
import sys
import json
import subprocess
from pathlib import Path

def install_components() -> None:
    # 1. Resolve OEDISI_COMPONENTS
    components_root = os.environ.get("OEDISI_COMPONENTS")
    if not components_root:
        print("\nError: The OEDISI_COMPONENTS environment variable is not set.", file=sys.stderr)
        print("Please set it to the path of your local OEDISI Components directory.", file=sys.stderr)
        print("Example: export OEDISI_COMPONENTS=\"$HOME/dev/oedisi-components/Components\"\n", file=sys.stderr)
        sys.exit(1)

    components_root_path = Path(components_root).resolve()
    if not components_root_path.exists():
        print(f"Error: OEDISI_COMPONENTS directory not found at: {components_root_path}", file=sys.stderr)
        sys.exit(1)

    # 2. Load server/components.json
    server_dir = Path(__file__).resolve().parent
    components_json_path = server_dir / "components.json"
    if not components_json_path.exists():
        print(f"Error: components.json not found at: {components_json_path}", file=sys.stderr)
        sys.exit(1)

    with open(components_json_path, "r", encoding="utf-8") as f:
        try:
            mapping = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"Error parsing components.json: {exc}", file=sys.stderr)
            sys.exit(1)

    # 3. Collect component directories
    component_dirs = []
    # Always include the broker first
    broker_dir = components_root_path / "broker"
    if broker_dir.exists():
        component_dirs.append(broker_dir)

    for name, raw_path in mapping.items():
        if "${OEDISI_COMPONENTS}" in raw_path:
            resolved_path = raw_path.replace("${OEDISI_COMPONENTS}", str(components_root_path))
            comp_def_path = Path(resolved_path).resolve()
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

    # 4. Install them using uv pip install -e
    print(f"Installing {len(component_dirs)} components into virtual environment...")
    failed_components = []
    for comp_dir in component_dirs:
        print(f"  Installing {comp_dir.name} ({comp_dir})...")
        try:
            subprocess.run(
                ["uv", "pip", "install", "-e", str(comp_dir)],
                cwd=server_dir,
                check=True
            )
        except subprocess.CalledProcessError as exc:
            print(f"Warning: Failed to install component {comp_dir.name} ({exc}). Skipping.", file=sys.stderr)
            failed_components.append(comp_dir.name)

    if failed_components:
        print(f"\nCompleted with warnings. The following components failed to install: {', '.join(failed_components)}")
    else:
        print("\nAll components installed successfully!")

if __name__ == "__main__":
    install_components()
