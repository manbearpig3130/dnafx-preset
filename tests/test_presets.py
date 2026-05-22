import unittest

from dnafx_preset.presets import PresetCatalog


class PresetCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = PresetCatalog.load()

    def test_loads_numeric_slots(self) -> None:
        self.assertEqual(self.catalog.slot_count, 201)

    def test_resolves_slot_by_user_index(self) -> None:
        selection = self.catalog.resolve("1")
        self.assertEqual(selection.slot_number, 1)
        self.assertEqual(selection.key, "0")

    def test_rejects_non_numeric_lookup(self) -> None:
        with self.assertRaisesRegex(ValueError, "Preset number must be numeric"):
            self.catalog.resolve("GRANDI AFFARI")

    def test_preserves_variable_payload_length(self) -> None:
        selection = self.catalog.resolve("201")
        self.assertEqual(selection.slot_number, 201)
        self.assertEqual(len(selection.payload), 10)


if __name__ == "__main__":
    unittest.main()