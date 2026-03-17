#!/usr/bin/env python3
"""Export oedisi type hierarchy to JSON for portCompatibility.ts."""

import inspect
import json
from pathlib import Path

from oedisi.types import data_types, common
from pydantic import BaseModel

MODULES = [data_types, common]


def get_immediate_parent(cls, all_class_names):
    """Return immediate parent name if it's in our set, else None."""
    for parent in cls.__mro__[1:]:
        if parent is object or parent is BaseModel:
            return None
        if parent.__name__ in all_class_names:
            return parent.__name__
    return None


def main():
    # Gather all classes defined in our modules
    classes = [
        (name, cls)
        for module in MODULES
        for name, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__
    ]
    all_names = {name for name, _ in classes}

    # Build parent mapping
    type_parents = {name: get_immediate_parent(cls, all_names) for name, cls in classes}

    # Write JSON
    output_path = Path(__file__).parent.parent / "src" / "lib" / "typeHierarchy.json"
    output_path.write_text(json.dumps(type_parents, indent=2, sort_keys=True))
    print(f"Exported to {output_path}")


if __name__ == "__main__":
    main()
