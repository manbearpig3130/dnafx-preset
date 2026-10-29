from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import json

# RS Companion's song tone message (docs/song-tone-messages.md in glebb/rs-mac-companion): when an
# arrangement loads, one SysEx F0 7D <JSON> F7 lists the song's tones, and during the song each tone
# plays on its own Program Change.

NON_COMMERCIAL_ID = 0x7D
CATEGORIES = ("Clean", "Crunch", "Heavy", "Lead")


@dataclass(frozen=True)
class SongTone:
    program: int
    key: str
    category: str
    modulation: str | None = None  # chorus, flanger, phaser, tremolo or vibe
    delay: str | None = None  # tape, analog, modulated or digital


@dataclass(frozen=True)
class SongTones:
    song: str
    artist: str
    arrangement: str
    style: str | None
    tones: tuple[SongTone, ...]

    def same_arrangement(self, other: SongTones | None) -> bool:
        return other is not None and (self.song, self.artist, self.arrangement) == (
            other.song,
            other.artist,
            other.arrangement,
        )


def parse_song_tones(message: Sequence[int]) -> SongTones | None:
    # None for any other SysEx, kind or version
    if len(message) < 3 or message[0] != 0xF0 or message[1] != NON_COMMERCIAL_ID or message[-1] != 0xF7:
        return None
    try:
        data = json.loads(bytes(message[2:-1]).decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "song-tones" or data.get("v") != 2:
        return None

    tones: list[SongTone] = []
    for raw in data.get("tones") or []:
        if not isinstance(raw, dict):
            continue
        program, category = raw.get("program"), raw.get("category")
        if not isinstance(program, int) or not 0 <= program <= 127 or category not in CATEGORIES:
            continue
        effects = raw.get("effects")
        if not isinstance(effects, dict):
            effects = {}
        tones.append(
            SongTone(
                program=program,
                key=str(raw.get("key", "")),
                category=category,
                modulation=_effect_kind(effects, "modulation"),
                delay=_effect_kind(effects, "delay"),
            )
        )

    style = data.get("style")
    return SongTones(
        song=str(data.get("song", "")),
        artist=str(data.get("artist", "")),
        arrangement=str(data.get("arrangement", "")),
        style=style if isinstance(style, str) else None,
        tones=tuple(tones),
    )


def _effect_kind(effects: dict[object, object], name: str) -> str | None:
    effect = effects.get(name)
    if not isinstance(effect, dict):
        return None
    kind = effect.get("kind")
    return kind if isinstance(kind, str) else name
