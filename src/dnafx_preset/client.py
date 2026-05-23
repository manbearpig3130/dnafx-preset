from __future__ import annotations

from .config import DeviceConfig
from .presets import PresetCatalog, PresetSelection
from .transport import TransportProtocol, USBTransport


class DnafxPresetClient:
    def __init__(
        self,
        config: DeviceConfig,
        *,
        catalog: PresetCatalog | None = None,
        transport: TransportProtocol | None = None,
    ):
        self.config = config
        self.catalog = catalog or PresetCatalog.load(config.presets_file)
        if transport is not None:
            self.transport = transport
        else:
            self.transport = USBTransport(
                vendor_id=config.vendor_id,
                product_id=config.product_id,
                out_endpoint=config.out_endpoint,
            )

    def switch(self, identifier: str | int) -> PresetSelection:
        selection = self.catalog.resolve(identifier)
        self.transport.send_payload(selection.payload)
        return selection