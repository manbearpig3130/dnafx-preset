from io import StringIO
from unittest.mock import patch
import unittest

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


class CliTests(unittest.TestCase):
    def test_set_uses_client(self) -> None:
        stdout = StringIO()
        stderr = StringIO()

        with patch("dnafx_preset.cli.build_client", return_value=FakeClient()):
            exit_code = main(["set", "1"], stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertIn("Switched to slot 1", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_listen_uses_listener(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        listener = FakeListener(channel=0, port_name="DNAfx Preset In")

        with patch("dnafx_preset.cli.build_listener_with_error_handler", return_value=listener):
            exit_code = main(["listen"], stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(listener.listen_calls, 1)
        self.assertIn("Listening on virtual MIDI input 'DNAfx Preset In'", stdout.getvalue())
        self.assertIn("raw channels 0 and 1", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()