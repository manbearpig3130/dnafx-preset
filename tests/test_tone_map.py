from pathlib import Path

import pytest

from dnafx_preset.song_tones import parse_song_tones
from dnafx_preset.tone_map import ToneMap
from song_tone_samples import PURSUIT_OF_VIKINGS, ROOSTER, sysex

CONFIG = """
[categories]
Clean = 49
Crunch = 50
Heavy = 51
Lead = 187

[effects.clean]
flanger = 60

[effects.Lead]
modulation = 188

[styles.Metal]
Heavy = 52

[artists."amon amarth"]
Lead = 190

[songs.Rooster]
alicroos_dist = 70
lead = 71
"""


@pytest.fixture
def tone_map(tmp_path: Path) -> ToneMap:
    path = tmp_path / "tones.toml"
    path.write_text(CONFIG, encoding="utf-8")
    return ToneMap.load(path)


def choices(tone_map: ToneMap, data: dict[str, object]) -> list[tuple[int, str] | None]:
    song = parse_song_tones(sysex(data))
    assert song is not None
    result: list[tuple[int, str] | None] = []
    for tone in song.tones:
        choice = tone_map.choose(song, tone)
        result.append((choice.slot_number, choice.rule) if choice else None)
    return result


def test_song_rules_come_first_then_effects(tone_map: ToneMap) -> None:
    assert choices(tone_map, ROOSTER) == [
        (60, "effect flanger"),
        (70, "song 'Rooster', tone alicroos_dist"),
        (71, "song 'Rooster'"),
    ]


def test_artist_rules_come_before_styles_then_categories(tone_map: ToneMap) -> None:
    assert choices(tone_map, PURSUIT_OF_VIKINGS) == [(52, "style 'Metal'"), (190, "artist 'amon amarth'")]


def test_falls_back_to_the_category(tone_map: ToneMap) -> None:
    data = {**PURSUIT_OF_VIKINGS, "artist": "Someone", "style": "Soft"}

    assert choices(tone_map, data) == [(51, "category"), (187, "category")]


def test_no_rule_means_no_slot() -> None:
    assert choices(ToneMap(), ROOSTER) == [None, None, None]


def test_lists_its_slots(tone_map: ToneMap) -> None:
    assert sorted(tone_map.slots()) == [49, 50, 51, 52, 60, 70, 71, 187, 188, 190]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"presets": {}}, "Unknown section 'presets'"),
        ({"categories": {"Acoustic": 1}}, "Unknown category 'categories.Acoustic'"),
        ({"effects": {"Clean": {"reverb": 1}}}, "Unknown effect 'effects.Clean.reverb'"),
        ({"styles": {"Metal": {"Heavy": 0}}}, "'styles.Metal.Heavy' must be a slot number"),
        ({"artists": {"X": {"Heavy": "51"}}}, "'artists.X.Heavy' must be a slot number"),
        ({"songs": {"X": {"Heavy": True}}}, "'songs.X.Heavy' must be a slot number"),
        ({"categories": 3}, "'categories' must be a table"),
    ],
)
def test_rejects_invalid_rules(data: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ToneMap.from_dict(data)


def test_rejects_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "tones.toml"
    path.write_text("[categories\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid TOML"):
        ToneMap.load(path)
