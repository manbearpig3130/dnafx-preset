import json
from pathlib import Path

import pytest

from dnafx_preset.presets import PresetCatalog
from dnafx_preset.protocol import preset_change_message


@pytest.fixture
def catalog() -> PresetCatalog:
    return PresetCatalog.load()


def test_loads_numeric_slots(catalog: PresetCatalog) -> None:
    assert catalog.slot_count == 200


def test_resolves_slot_by_user_index(catalog: PresetCatalog) -> None:
    selection = catalog.resolve("1")
    assert selection.slot_number == 1
    assert selection.key == "0"


def test_rejects_non_numeric_lookup(catalog: PresetCatalog) -> None:
    with pytest.raises(ValueError, match="Preset number must be numeric"):
        catalog.resolve("GRANDI AFFARI")


def test_default_payloads_are_computed_preset_change_messages(catalog: PresetCatalog) -> None:
    for slot_number in (1, 96, 200):
        assert catalog.resolve(str(slot_number)).payload == preset_change_message(slot_number)


def test_rejects_slot_201(catalog: PresetCatalog) -> None:
    with pytest.raises(IndexError, match="between 1 and 200"):
        catalog.resolve("201")


def test_presets_file_preserves_variable_payload_length(tmp_path: Path) -> None:
    presets_file = tmp_path / "presets.json"
    presets_file.write_text(json.dumps({"0": [8, 170, 85, 2, 0, 150, 1, 176, 251, 0]}), encoding="utf-8")

    selection = PresetCatalog.load(presets_file).resolve("1")

    assert selection.payload == bytes([8, 170, 85, 2, 0, 150, 1, 176, 251, 0])