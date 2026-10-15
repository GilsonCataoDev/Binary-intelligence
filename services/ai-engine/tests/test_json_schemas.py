import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_DIR = Path(__file__).parents[3] / "packages" / "contracts" / "schemas"


def test_contract_schemas_are_valid_draft_2020_12() -> None:
    paths = list(SCHEMA_DIR.glob("*.json"))
    assert len(paths) == 3
    for path in paths:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
