from argparse import Namespace
from io import StringIO
from unittest.mock import patch

from dnafx_preset.cli import main
from dnafx_preset.presets import PresetSelection


class FakeClient:
    def __init__(self) -> None:
        self._selection = PresetSelection(
            key="0",
            slot_number=1,
            payload=b"\x08\xaa\x55",
        )

    def switch(self, _target: str) -> PresetSelection:
        return self._selection


class FakeListener:
    def __init__(
        self,
        *,
        channel: int = 0,
        port_name: str = "DNAfx Preset In",
        source_name: str | None = None,
    ) -> None:
        self.channel = channel
        self.port_name = port_name
        self.source_name = source_name
        self.listen_calls = 0

    def listen(self) -> None:
        self.listen_calls += 1


def test_set_uses_client() -> None:
    stdout = StringIO()
    stderr = StringIO()

    with patch("dnafx_preset.cli.build_client", return_value=FakeClient()):
        exit_code = main(["set", "1"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert "Switched to slot 1" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_listen_uses_listener() -> None:
    stdout = StringIO()
    stderr = StringIO()
    listener = FakeListener(channel=0, port_name="DNAfx Preset In")

    with patch("dnafx_preset.cli.build_listener", return_value=listener):
        exit_code = main(["listen"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert listener.listen_calls == 1
    assert "Listening on virtual MIDI input 'DNAfx Preset In'" in stdout.getvalue()
    assert "raw channels 0 and 1" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_listen_connects_to_midi_source() -> None:
    stdout = StringIO()
    stderr = StringIO()
    listeners: list[FakeListener] = []

    def fake_build_listener(args: Namespace, *_handlers: object) -> FakeListener:
        listeners.append(FakeListener(source_name=args.midi_source))
        return listeners[-1]

    with patch("dnafx_preset.cli.build_listener", side_effect=fake_build_listener):
        exit_code = main(["listen", "--midi-source", "Rocksmith Companion"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert listeners[0].listen_calls == 1
    assert "Listening to MIDI source 'Rocksmith Companion'" in stdout.getvalue()


def test_transport_option_rejects_unknown_values() -> None:
    import pytest

    with pytest.raises(SystemExit):
        main(["--transport", "serial", "set", "1"], stdout=StringIO(), stderr=StringIO())


def test_listen_passes_program_map_to_the_listener_config() -> None:
    from dnafx_preset.cli import build_listener_config, build_parser

    args = build_parser().parse_args(["listen", "--midi-program-map", "0=49,1=50,2=51,3=187"])

    assert build_listener_config(args).program_map == ((0, 49), (1, 50), (2, 51), (3, 187))
