import unittest

from dnafx_preset.client import DnafxPresetClient
from dnafx_preset.config import DeviceConfig


class FakeTransport:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    def send_payload(self, payload: bytes) -> None:
        self.payloads.append(payload)


class DnafxPresetClientTests(unittest.TestCase):
    def test_switch_sends_payload(self) -> None:
        config = DeviceConfig(
            vendor_id=0x0483,
            product_id=0x5703,
            out_endpoint=0x02,
            presets_file=None,
        )
        transport = FakeTransport()
        client = DnafxPresetClient(config, transport=transport)

        selection = client.switch("1")

        self.assertEqual(selection.slot_number, 1)
        self.assertEqual(len(transport.payloads), 1)

    def test_rejects_non_numeric_target(self) -> None:
        config = DeviceConfig(
            vendor_id=0x0483,
            product_id=0x5703,
            out_endpoint=0x02,
            presets_file=None,
        )
        transport = FakeTransport()
        client = DnafxPresetClient(config, transport=transport)

        with self.assertRaisesRegex(ValueError, "Preset number must be numeric"):
            client.switch("GRANDI AFFARI")


if __name__ == "__main__":
    unittest.main()