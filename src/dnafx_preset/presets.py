from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .embedded_presets import DEFAULT_PRESET_PAYLOADS


@dataclass(frozen=True)
class PresetSelection:
    key: str
    slot_number: int | None
    payload: bytes


class PresetCatalog:
    def __init__(self, raw_presets: dict[str, object] | tuple[tuple[int, ...], ...]):
        if not raw_presets:
            raise ValueError("Preset catalog is empty")

        self._slots: list[PresetSelection] = []

        if isinstance(raw_presets, tuple):
            for position, payload in enumerate(raw_presets, start=1):
                selection = PresetSelection(
                    key=str(position - 1),
                    slot_number=position,
                    payload=self._coerce_payload(list(payload), str(position - 1)),
                )
                self._slots.append(selection)
            return

        numeric_keys = sorted((key for key in raw_presets if key.isdigit()), key=int)
        if not numeric_keys:
            raise ValueError("Preset catalog does not contain numeric slots")

        for position, key in enumerate(numeric_keys, start=1):
            payload = self._coerce_payload(raw_presets[key], key)
            selection = PresetSelection(key=key, slot_number=position, payload=payload)
            self._slots.append(selection)

    @classmethod
    def load(cls, presets_file: Path | None = None) -> "PresetCatalog":
        if presets_file is None:
            return cls(DEFAULT_PRESET_PAYLOADS)

        raw_text = Path(presets_file).read_text(encoding="utf-8")
        raw_presets = json.loads(raw_text)
        if not isinstance(raw_presets, dict):
            raise ValueError("Preset file must contain a JSON object")
        return cls(raw_presets)

    @property
    def slot_count(self) -> int:
        return len(self._slots)

    def resolve(self, identifier: str | int) -> PresetSelection:
        if isinstance(identifier, int):
            return self.get_slot(identifier)

        raw_identifier = identifier.strip()
        if not raw_identifier:
            raise ValueError("Preset identifier cannot be empty")

        if raw_identifier.isdigit():
            return self.get_slot(int(raw_identifier))

        raise ValueError(f"Preset number must be numeric: {identifier}")

    def get_slot(self, slot_number: int) -> PresetSelection:
        if slot_number < 1 or slot_number > self.slot_count:
            raise IndexError(f"Slot must be between 1 and {self.slot_count}")
        return self._slots[slot_number - 1]

    @staticmethod
    def _coerce_payload(value: object, key: str) -> bytes:
        if not isinstance(value, list) or not value:
            raise ValueError(f"Preset payload for {key} must be a non-empty list")

        if not all(isinstance(item, int) and 0 <= item <= 255 for item in value):
            raise ValueError(f"Preset payload for {key} must contain byte values")

        return bytes(value)