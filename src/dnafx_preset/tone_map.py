from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .song_tones import CATEGORIES, SongTone, SongTones

# A tone's modulation kind, then any modulation, then delay. Reverb is left out: most tones have some.
EFFECTS = ("chorus", "flanger", "phaser", "tremolo", "vibe", "modulation", "delay")
SECTIONS = ("categories", "effects", "styles", "artists", "songs")


@dataclass(frozen=True)
class ToneChoice:
    slot_number: int
    rule: str


@dataclass(frozen=True)
class ToneMap:
    # Rules for picking a slot for each of a song's tones. The first match wins, in this order:
    # songs (tone key, then category), artists, effects, styles, categories.
    categories: tuple[tuple[str, int], ...] = ()
    effects: tuple[tuple[str, str, int], ...] = ()  # (category, effect, slot)
    styles: tuple[tuple[str, str, int], ...] = ()  # (style, category, slot)
    artists: tuple[tuple[str, str, int], ...] = ()  # (artist, category, slot)
    songs: tuple[tuple[str, str, int], ...] = ()  # (song, tone key or category, slot)

    @classmethod
    def load(cls, path: Path) -> ToneMap:
        with open(path, "rb") as file:
            try:
                data = tomllib.load(file)
            except tomllib.TOMLDecodeError as exc:
                raise ValueError(f"Invalid TOML in {path}: {exc}") from exc
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ToneMap:
        for section in data:
            if section not in SECTIONS:
                raise ValueError(f"Unknown section '{section}'; sections are {', '.join(SECTIONS)}")

        categories = tuple(
            (_category(name, f"categories.{name}"), _slot(value, f"categories.{name}"))
            for name, value in _table(data.get("categories", {}), "categories").items()
        )

        effects: list[tuple[str, str, int]] = []
        for category_name, table in _table(data.get("effects", {}), "effects").items():
            category = _category(category_name, f"effects.{category_name}")
            for effect, value in _table(table, f"effects.{category_name}").items():
                path = f"effects.{category_name}.{effect}"
                if effect.lower() not in EFFECTS:
                    raise ValueError(f"Unknown effect '{path}'; effects are {', '.join(EFFECTS)}")
                effects.append((category, effect.lower(), _slot(value, path)))

        named: dict[str, list[tuple[str, str, int]]] = {"styles": [], "artists": []}
        for section, rows in named.items():
            for name, table in _table(data.get(section, {}), section).items():
                for category_name, value in _table(table, f"{section}.{name}").items():
                    path = f"{section}.{name}.{category_name}"
                    rows.append((name, _category(category_name, path), _slot(value, path)))

        songs: list[tuple[str, str, int]] = []
        for name, table in _table(data.get("songs", {}), "songs").items():
            for key, value in _table(table, f"songs.{name}").items():
                category = _match(key, CATEGORIES)
                songs.append((name, category or key, _slot(value, f"songs.{name}.{key}")))

        return cls(
            categories=categories,
            effects=tuple(effects),
            styles=tuple(named["styles"]),
            artists=tuple(named["artists"]),
            songs=tuple(songs),
        )

    def slots(self) -> list[int]:
        return [row[-1] for rows in (self.categories, self.effects, self.styles, self.artists, self.songs) for row in rows]

    def choose(self, song: SongTones, tone: SongTone) -> ToneChoice | None:
        for name, key, slot in self.songs:
            if _same(name, song.song) and _same(key, tone.key):
                return ToneChoice(slot, f"song '{name}', tone {tone.key}")
        for name, category, slot in self.songs:
            if _same(name, song.song) and category == tone.category:
                return ToneChoice(slot, f"song '{name}'")
        for name, category, slot in self.artists:
            if _same(name, song.artist) and category == tone.category:
                return ToneChoice(slot, f"artist '{name}'")

        tone_effects = [effect for effect in (tone.modulation, "modulation" if tone.modulation else None) if effect]
        tone_effects += ["delay"] if tone.delay else []
        for effect in tone_effects:
            for category, wanted, slot in self.effects:
                if category == tone.category and wanted == effect.lower():
                    return ToneChoice(slot, f"effect {effect}")

        for name, category, slot in self.styles:
            if song.style is not None and _same(name, song.style) and category == tone.category:
                return ToneChoice(slot, f"style '{name}'")
        for category, slot in self.categories:
            if category == tone.category:
                return ToneChoice(slot, "category")
        return None


def _same(a: str, b: str) -> bool:
    return a.casefold() == b.casefold()


def _match(name: str, choices: tuple[str, ...]) -> str | None:
    return next((choice for choice in choices if _same(choice, name)), None)


def _table(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"'{path}' must be a table")
    return value


def _category(name: str, path: str) -> str:
    category = _match(name, CATEGORIES)
    if category is None:
        raise ValueError(f"Unknown category '{path}'; categories are {', '.join(CATEGORIES)}")
    return category


def _slot(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"'{path}' must be a slot number, 1 or more")
    return value
