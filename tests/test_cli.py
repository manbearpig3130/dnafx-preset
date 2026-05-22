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

    def next(self) -> PresetSelection:
        return self._selection

    def previous(self) -> PresetSelection:
        return self._selection


class FakeListener:
    def __init__(self, *, channel: int = 0, port_name: str = "DNAfx Preset In") -> None:
        self.channel = channel
        self.port_name = port_name
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

    with patch("dnafx_preset.cli.build_listener_with_error_handler", return_value=listener):
        exit_code = main(["listen"], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert listener.listen_calls == 1
    assert "Listening on virtual MIDI input 'DNAfx Preset In'" in stdout.getvalue()
    assert "raw channels 0 and 1" in stdout.getvalue()
    assert stderr.getvalue() == ""