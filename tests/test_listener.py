from dnafx_preset.listener import MidiProgramChangeListener


class FakeCatalog:
    def __init__(self, slot_count: int) -> None:
        self.slot_count = slot_count


class FakeClient:
    def __init__(self, slot_count: int = 200) -> None:
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

    def get_ports(self) -> list[str]:
        return []

    def open_port(self, port: int = 0, name: str | None = None) -> None:
        raise AssertionError("a virtual input never opens another port")

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
    client = FakeClient(slot_count=200)
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


class FakeSourceMidiIn(FakeMidiIn):
    # get_ports() returns the next list from port_lists each time, repeating the last one
    def __init__(
        self,
        port_lists: list[list[str]],
        messages: list[tuple[list[int], float] | None | BaseException],
    ) -> None:
        super().__init__(messages)
        self._port_lists = list(port_lists)
        self.opened_ports: list[tuple[int, str | None]] = []
        self.close_calls = 0

    def get_ports(self) -> list[str]:
        if len(self._port_lists) > 1:
            return self._port_lists.pop(0)
        return self._port_lists[0]

    def open_port(self, port: int = 0, name: str | None = None) -> None:
        self.opened_ports.append((port, name))

    def close_port(self) -> None:
        super().close_port()
        self.close_calls += 1


def make_source_listener(
    client: FakeClient,
    midi_in: FakeSourceMidiIn,
    statuses: list[str],
    source_name: str = "rocksmith companion",
) -> MidiProgramChangeListener:
    return MidiProgramChangeListener(
        client,
        channel=0,
        source_name=source_name,
        midi_in_factory=lambda: midi_in,
        status_handler=statuses.append,
        idle_sleep=0.0,
        source_check_interval=0.0,
    )


def test_listen_connects_to_a_named_source() -> None:
    client = FakeClient()
    statuses: list[str] = []
    midi_in = FakeSourceMidiIn([["IAC Driver Bus 1", "Rocksmith Companion"]], [([0xC0, 50], 0.0)])

    make_source_listener(client, midi_in, statuses).listen()

    assert midi_in.opened_port_name is None
    assert midi_in.opened_ports == [(1, "DNAfx Preset In")]
    assert client.switch_calls == [51]
    assert statuses == ["Connected to MIDI source 'Rocksmith Companion'", "Switched to slot 51"]
    assert midi_in.closed is True


def test_listen_waits_for_the_source_to_appear() -> None:
    client = FakeClient()
    statuses: list[str] = []
    midi_in = FakeSourceMidiIn([[], ["IAC Driver Bus 1"], ["Rocksmith Companion"]], [([0xC0, 0], 0.0)])

    make_source_listener(client, midi_in, statuses).listen()

    assert statuses == [
        "Waiting for a MIDI source named 'rocksmith companion'",
        "Connected to MIDI source 'Rocksmith Companion'",
        "Switched to slot 1",
    ]
    assert client.switch_calls == [1]


def test_listen_reconnects_when_the_source_comes_back() -> None:
    client = FakeClient()
    statuses: list[str] = []
    midi_in = FakeSourceMidiIn(
        [["Rocksmith Companion"], [], ["Launchkey", "Rocksmith Companion"]],
        [None, ([0xC0, 3], 0.0)],
    )

    make_source_listener(client, midi_in, statuses).listen()

    assert midi_in.opened_ports == [(0, "DNAfx Preset In"), (1, "DNAfx Preset In")]
    assert statuses == [
        "Connected to MIDI source 'Rocksmith Companion'",
        "MIDI source 'Rocksmith Companion' went away; waiting for it to come back",
        "Connected to MIDI source 'Rocksmith Companion'",
        "Switched to slot 4",
    ]
    assert client.switch_calls == [4]
    assert midi_in.close_calls == 2


def test_listen_reports_switches_but_not_ignored_messages() -> None:
    statuses: list[str] = []
    midi_in = FakeMidiIn([([0xC0, 4], 0.0), ([0xC5, 4], 0.0), ([0xB0, 7, 100], 0.0)])
    listener = MidiProgramChangeListener(
        FakeClient(),
        channel=0,
        midi_in_factory=lambda: midi_in,
        status_handler=statuses.append,
        idle_sleep=0.0,
    )

    listener.listen()

    assert statuses == ["Switched to slot 5"]


def test_program_map_overrides_the_base_channel_rule() -> None:
    client = FakeClient()
    listener = MidiProgramChangeListener(client, channel=0, program_map=((2, 51), (3, 187)))

    assert listener.process_message([0xC0, 3]) == 187
    assert listener.process_message([0xC0, 2]) == 51
    assert listener.process_message([0xC0, 4]) == 5
    assert listener.process_message([0xC1, 3]) == 132
    assert client.switch_calls == [187, 51, 5, 132]


def test_program_map_rejects_slots_the_device_does_not_have() -> None:
    import pytest

    with pytest.raises(ValueError, match="slots are 1 to 200"):
        MidiProgramChangeListener(FakeClient(slot_count=200), program_map=((0, 201),))
