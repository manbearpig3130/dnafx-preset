from dnafx_preset.listener import MidiProgramChangeListener


class FakeCatalog:
    def __init__(self, slot_count: int) -> None:
        self.slot_count = slot_count


class FakeClient:
    def __init__(self, slot_count: int = 201) -> None:
        self.catalog = FakeCatalog(slot_count)
        self.switch_calls: list[int] = []

    def switch(self, target: int) -> None:
        self.switch_calls.append(target)


class RaisingClient(FakeClient):
    def switch(self, target: int) -> None:
        raise RuntimeError(f"unable to switch to {target}")


class FakeMidiIn:
    def __init__(self, messages: list[tuple[list[int], float] | None | BaseException]) -> None:
        self._messages = list(messages)
        self.opened_port_name: str | None = None
        self.closed = False

    def open_virtual_port(self, port_name: str) -> None:
        self.opened_port_name = port_name

    def get_message(self) -> tuple[list[int], float] | None:
        if not self._messages:
            raise KeyboardInterrupt()

        next_item = self._messages.pop(0)
        if isinstance(next_item, BaseException):
            raise next_item
        return next_item

    def close_port(self) -> None:
        self.closed = True


def test_program_change_maps_to_first_bank_slots() -> None:
    client = FakeClient()
    listener = MidiProgramChangeListener(client, channel=0)

    slot_number = listener.process_message([0xC0, 0])

    assert slot_number == 1
    assert client.switch_calls == [1]


def test_wrong_channel_is_ignored() -> None:
    client = FakeClient()
    listener = MidiProgramChangeListener(client, channel=0)

    slot_number = listener.process_message([0xC2, 0])

    assert slot_number is None
    assert client.switch_calls == []


def test_next_channel_selects_upper_bank() -> None:
    client = FakeClient()
    listener = MidiProgramChangeListener(client, channel=0)

    slot_number = listener.process_message([0xC1, 0])

    assert slot_number == 129
    assert client.switch_calls == [129]


def test_configured_base_channel_uses_next_channel_for_upper_bank() -> None:
    client = FakeClient()
    listener = MidiProgramChangeListener(client, channel=2)

    slot_number = listener.process_message([0xC3, 0])

    assert slot_number == 129
    assert client.switch_calls == [129]


def test_out_of_range_bank_program_is_ignored() -> None:
    client = FakeClient(slot_count=201)
    listener = MidiProgramChangeListener(client, channel=0)

    slot_number = listener.process_message([0xC1, 127])

    assert slot_number is None
    assert client.switch_calls == []


def test_listen_reports_switch_errors_and_keeps_port_open() -> None:
    errors: list[str] = []
    midi_in = FakeMidiIn([([0xC0, 0], 0.0), KeyboardInterrupt()])
    listener = MidiProgramChangeListener(
        RaisingClient(),
        channel=0,
        midi_in_factory=lambda: midi_in,
        error_handler=lambda exc: errors.append(str(exc)),
        idle_sleep=0.0,
    )

    listener.listen()

    assert midi_in.opened_port_name == "DNAfx Preset In"
    assert errors == ["unable to switch to 1"]
    assert midi_in.closed is True