from __future__ import annotations

import time
from typing import Callable, Protocol, Sequence, cast


class MidiInputProtocol(Protocol):
    def open_virtual_port(self, port_name: str) -> None:
        ...

    def get_message(self) -> tuple[list[int], float] | None:
        ...

    def close_port(self) -> None:
        ...


class PresetCatalogProtocol(Protocol):
    @property
    def slot_count(self) -> int:
        ...


class PresetSwitchingClientProtocol(Protocol):
    @property
    def catalog(self) -> PresetCatalogProtocol:
        ...

    def switch(self, identifier: int | str, /) -> object:
        ...


class MidiListenerError(RuntimeError):
    pass


class MidiProgramChangeListener:
    def __init__(
        self,
        client: PresetSwitchingClientProtocol,
        *,
        channel: int = 0,
        port_name: str = "DNAfx Preset In",
        slot_count: int | None = None,
        midi_in_factory: Callable[[], MidiInputProtocol] | None = None,
        error_handler: Callable[[Exception], None] | None = None,
        idle_sleep: float = 0.01,
    ):
        resolved_slot_count = slot_count if slot_count is not None else self._infer_slot_count(client)
        if resolved_slot_count < 1:
            raise ValueError("Slot count must be at least 1")

        self.client = client
        self.channel = channel
        self.port_name = port_name
        self.slot_count = resolved_slot_count
        self._midi_in_factory = midi_in_factory or self._default_midi_in_factory
        self._error_handler = error_handler
        self._idle_sleep = idle_sleep

    def process_message(self, message: Sequence[int]) -> int | None:
        if not message:
            return None

        status = message[0]
        message_type = status & 0xF0
        if message_type != 0xC0 or len(message) < 2:
            return None

        incoming_channel = status & 0x0F
        bank = self._resolve_bank(incoming_channel)
        if bank is None:
            return None

        program = message[1]
        slot_number = self._resolve_slot_number(program, bank)
        if slot_number is None:
            return None

        self.client.switch(slot_number)
        return slot_number

    def listen(self) -> None:
        midi_in = self._midi_in_factory()
        try:
            midi_in.open_virtual_port(self.port_name)
        except Exception as exc:
            raise MidiListenerError(f"Unable to open virtual MIDI input '{self.port_name}': {exc}") from exc

        try:
            while True:
                message = midi_in.get_message()
                if message is None:
                    time.sleep(self._idle_sleep)
                    continue

                payload, _delta = message
                try:
                    self.process_message(payload)
                except Exception as exc:
                    if self._error_handler is not None:
                        self._error_handler(exc)
        except KeyboardInterrupt:
            return
        finally:
            self._close_midi_in(midi_in)

    def _resolve_bank(self, incoming_channel: int) -> int | None:
        if incoming_channel == self.channel:
            return 0
        if incoming_channel == self.channel + 1 and self.channel < 15:
            return 1
        return None

    def _resolve_slot_number(self, program: int, bank: int) -> int | None:
        if program < 0 or program > 127:
            return None

        slot_number = bank * 128 + program + 1
        if slot_number < 1 or slot_number > self.slot_count:
            return None
        return slot_number

    @staticmethod
    def _infer_slot_count(client: PresetSwitchingClientProtocol) -> int:
        slot_count = client.catalog.slot_count
        if slot_count < 1:
            raise ValueError("Slot count is required when the client does not expose catalog.slot_count")
        return slot_count

    @staticmethod
    def _default_midi_in_factory() -> MidiInputProtocol:
        try:
            import rtmidi
        except ImportError as exc:
            raise MidiListenerError(
                "python-rtmidi is required for MIDI listening. Install the package and rerun the command."
            ) from exc

        midi_in_factory = getattr(rtmidi, "MidiIn", None)
        if not callable(midi_in_factory):
            raise MidiListenerError("python-rtmidi does not expose MidiIn on this platform")

        return cast(MidiInputProtocol, midi_in_factory())

    @staticmethod
    def _close_midi_in(midi_in: MidiInputProtocol) -> None:
        midi_in.close_port()