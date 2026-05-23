---
applyTo: src/**
---

# Source Code Type Conventions

## `from __future__ import annotations` Is Always Present

Every source file has `from __future__ import annotations`. All annotations are therefore lazy strings by default. Do **not** wrap type annotations in quotes:

```python
# Wrong
def from_sources(cls) -> "DeviceConfig": ...

# Correct
def from_sources(cls) -> DeviceConfig: ...
```

## Frozen Dataclasses for Config and Result Types

Config and result types use `@dataclass(frozen=True)`. Do not add mutable fields:

```python
@dataclass(frozen=True)
class DeviceConfig:
    vendor_id: int
    product_id: int
    out_endpoint: int
    presets_file: Path | None
```

## `Protocol` for Injectable Dependencies

Use `typing.Protocol` (not `ABC`) for hardware and external dependencies. This lets tests pass plain structs without subclassing:

```python
class TransportProtocol(Protocol):
    def send_payload(self, payload: bytes) -> None: ...
```

## Slot Numbering

Slots are **1-based** in all public APIs. The internal `_slots` list is 0-indexed but is never exposed directly. Always document slot parameters as 1-based.

## USB ID Types

`vendor_id`, `product_id`, and `out_endpoint` are always `int` after parsing. `DeviceConfig.from_sources()` handles hex string conversion — callers never need to parse hex themselves.
