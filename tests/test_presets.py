import pytest

from dnafx_preset.presets import PresetCatalog


@pytest.fixture
def catalog() -> PresetCatalog:
    return PresetCatalog.load()


def test_loads_numeric_slots(catalog: PresetCatalog) -> None:
    assert catalog.slot_count == 201


def test_resolves_slot_by_user_index(catalog: PresetCatalog) -> None:
    selection = catalog.resolve("1")
    assert selection.slot_number == 1
    assert selection.key == "0"


def test_rejects_non_numeric_lookup(catalog: PresetCatalog) -> None:
    with pytest.raises(ValueError, match="Preset number must be numeric"):
        catalog.resolve("GRANDI AFFARI")


def test_preserves_variable_payload_length(catalog: PresetCatalog) -> None:
    selection = catalog.resolve("201")
    assert selection.slot_number == 201
    assert len(selection.payload) == 10