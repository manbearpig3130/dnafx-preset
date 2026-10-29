from __future__ import annotations

import time
from typing import Callable, Protocol, Sequence, cast


class MidiInputProtocol(Protocol):
    def open_virtual_port(self, port_name: str) -> None:
        ...

    def get_ports(self) -> list[str]:
        ...

    def open_port(self, port: int = 0, name: str | None = None) -> None:
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
        source_name: str | None = None,
        program_map: Sequence[tuple[int, int]] = (),
        slot_count: int | None = None,
        midi_in_factory: Callable[[], MidiInputProtocol] | None = None,
        error_handler: Callable[[Exception], None] | None = None,
        status_handler: Callable[[str], None] | None = None,
        idle_sleep: float = 0.01,
        source_check_interval: float = 1.0,
    ):
        resolved_slot_count = slot_count if slot_count is not None else self._infer_slot_count(client)
        if resolved_slot_count < 1:
            raise ValueError("Slot count must be at least 1")
        for program, slot_number in program_map:
            if slot_number < 1 or slot_number > resolved_slot_count:
                raise ValueError(f"Program {program} maps to slot {slot_number}; slots are 1 to {resolved_slot_count}")

        self.client = client
        self.channel = channel
        self.port_name = port_name
        self.source_name = source_name
        self.program_map = dict(program_map)
        self.slot_count = resolved_slot_count
        self._midi_in_factory = midi_in_factory or self._default_midi_in_factory
        self._error_handler = error_handler
        self._status_handler = status_handler
        self._idle_sleep = idle_sleep
        self._source_check_interval = source_check_interval

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
        if self.source_name is None:
            try:
                midi_in.open_virtual_port(self.port_name)
            except Exception as exc:
                raise MidiListenerError(f"Unable to open virtual MIDI input '{self.port_name}': {exc}") from exc

        try:
            if self.source_name is None:
                self._receive(midi_in)
            else:
                self._follow_source(midi_in, self.source_name)
        except KeyboardInterrupt:
            return
        finally:
            self._close_midi_in(midi_in)

    def _follow_source(self, midi_in: MidiInputProtocol, source_name: str) -> None:
        # Connect to another app's MIDI source (e.g. RS Companion's "Rocksmith Companion"), waiting for
        # it to appear, and connect again when the app quits and starts again.
        while True:
            index, port = self._wait_for_source(midi_in, source_name)
            try:
                midi_in.open_port(index, self.port_name)
            except Exception as exc:
                raise MidiListenerError(f"Unable to connect to MIDI source '{port}': {exc}") from exc

            self._report_status(f"Connected to MIDI source '{port}'")
            self._receive(midi_in, port)
            midi_in.close_port()
            self._report_status(f"MIDI source '{port}' went away; waiting for it to come back")

    def _wait_for_source(self, midi_in: MidiInputProtocol, source_name: str) -> tuple[int, str]:
        reported = False
        while True:
            wanted = source_name.casefold()
            for index, port in enumerate(midi_in.get_ports()):
                if wanted in port.casefold():
                    return index, port

            if not reported:
                self._report_status(f"Waiting for a MIDI source named '{source_name}'")
                reported = True
            time.sleep(self._source_check_interval)

    def _receive(self, midi_in: MidiInputProtocol, source_port: str | None = None) -> None:
        # Returns only when source_port is given and no longer exists
        next_check = time.monotonic() + self._source_check_interval
        while True:
            message = midi_in.get_message()
            if message is None:
                if source_port is not None and time.monotonic() >= next_check:
                    if source_port not in midi_in.get_ports():
                        return
                    next_check = time.monotonic() + self._source_check_interval
                time.sleep(self._idle_sleep)
                continue

            payload, _delta = message
            try:
                slot_number = self.process_message(payload)
            except Exception as exc:
                if self._error_handler is not None:
                    self._error_handler(exc)
                continue

            if slot_number is not None:
                self._report_status(f"Switched to slot {slot_number}")

    def _report_status(self, message: str) -> None:
        if self._status_handler is not None:
            self._status_handler(message)

    def _resolve_bank(self, incoming_channel: int) -> int | None:
        if incoming_channel == self.channel:
            return 0
        if incoming_channel == self.channel + 1 and self.channel < 15:
            return 1
        return None

    def _resolve_slot_number(self, program: int, bank: int) -> int | None:
        if program < 0 or program > 127:
            return None
        if bank == 0 and program in self.program_map:
            return self.program_map[program]

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