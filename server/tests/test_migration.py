"""Migration must reproduce the hand-edited templates on this branch.

Fixtures in fixtures/pre_migration/ are the pre-migration versions from main
(refresh with `git show main:data/templates/dev/<name>.json`).
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "server"))

from main import CONFIG_VERSION, _catalog_defaults, _migrate_template  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "pre_migration"
MIGRATED_DIR = REPO_ROOT / "data" / "templates" / "dev"

TEMPLATE_NAMES = [p.stem for p in sorted(FIXTURES.glob("*.json"))]


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_migration_matches_hand_edits(name: str) -> None:
    template = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    expected = json.loads((MIGRATED_DIR / f"{name}.json").read_text(encoding="utf-8"))

    assert _migrate_template(template, _catalog_defaults())
    assert template == {**expected, "config_version": CONFIG_VERSION}


def test_stamped_template_untouched() -> None:
    template = {"config_version": CONFIG_VERSION, "nodes": []}
    assert not _migrate_template(template, _catalog_defaults())
