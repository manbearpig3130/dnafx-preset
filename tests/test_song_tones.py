import pytest

from dnafx_preset.song_tones import SongTone, parse_song_tones
from song_tone_samples import PURSUIT_OF_VIKINGS, ROOSTER, sysex


def test_parses_a_song_tone_message() -> None:
    song = parse_song_tones(sysex(ROOSTER))

    assert song is not None
    assert (song.song, song.artist, song.arrangement, song.style) == ("Rooster", "Alice in Chains", "alicroos_rhythm", "Soft")
    assert song.tones == (
        SongTone(program=8, key="alicroos_cleanmod", category="Clean", modulation="flanger"),
        SongTone(program=9, key="alicroos_dist", category="Crunch"),
        SongTone(program=10, key="alicroos_leadmod", category="Lead", modulation="phaser"),
    )


def test_an_effect_without_a_kind_is_named_after_the_effect() -> None:
    data = {**PURSUIT_OF_VIKINGS, "tones": [{"program": 8, "key": "k", "category": "Lead", "effects": {"delay": {"mix": 20}}}]}

    song = parse_song_tones(sysex(data))

    assert song is not None and song.tones[0].delay == "delay"


@pytest.mark.parametrize(
    "message",
    [
        sysex(ROOSTER, manufacturer=0x41),
        sysex({**ROOSTER, "kind": "something-else"}),
        sysex({**ROOSTER, "v": 1}),
        [0xF0, 0x7D] + list(b"{not json") + [0xF7],
        sysex(ROOSTER)[:-1],
        [0xC0, 8],
    ],
)
def test_ignores_other_messages(message: list[int]) -> None:
    assert parse_song_tones(message) is None


def test_skips_tones_it_cannot_use() -> None:
    data = {**ROOSTER, "tones": [{"program": 8, "category": "Acoustic"}, {"program": 200, "category": "Clean"}, "x",
                                 {"program": 9, "key": "ok", "category": "Clean"}]}

    song = parse_song_tones(sysex(data))

    assert song is not None and [tone.program for tone in song.tones] == [9]
