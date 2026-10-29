import json

# Song tone messages RS Companion 1.4.2 sent while playing these songs
ROOSTER = {
    "arrangement": "alicroos_rhythm", "artist": "Alice in Chains", "heaviness": 0.01, "kind": "song-tones",
    "low_string": -1, "song": "Rooster", "style": "Soft", "styles": ["Soft", "Classic rock", "Metal"], "tempo": 144,
    "tones": [
        {"category": "Clean", "effects": {"modulation": {"gear": "Pedal_ModernFlanger", "kind": "flanger", "mix": 39, "rate": 33},
                                          "reverb": {"gear": "Pedal_DigitalVerb", "mix": 22}},
         "key": "alicroos_cleanmod", "program": 8},
        {"category": "Crunch", "effects": {"reverb": {"gear": "Pedal_DigitalVerb", "mix": 22}},
         "key": "alicroos_dist", "program": 9},
        {"category": "Lead", "effects": {"modulation": {"gear": "Pedal_Phaser", "kind": "phaser", "rate": 83},
                                         "reverb": {"gear": "Pedal_DigitalVerb", "mix": 22}},
         "key": "alicroos_leadmod", "program": 10},
    ],
    "v": 2,
}
PURSUIT_OF_VIKINGS = {
    "arrangement": "amonpurs_lead", "artist": "Amon Amarth", "heaviness": 0.83, "kind": "song-tones",
    "low_string": -5, "song": "The Pursuit of Vikings", "style": "Metal", "styles": ["Soft", "Classic rock", "Metal"],
    "tempo": 129,
    "tones": [
        {"category": "Heavy", "effects": {"reverb": {"gear": "Rack_StudioChamber", "mix": 11}}, "key": "amonpurs_dist", "program": 8},
        {"category": "Lead", "effects": {"reverb": {"gear": "Rack_StudioChamber", "mix": 19}}, "key": "amonpurs_lead", "program": 9},
    ],
    "v": 2,
}


def sysex(data: object, manufacturer: int = 0x7D) -> list[int]:
    return [0xF0, manufacturer] + list(json.dumps(data, ensure_ascii=True).encode("ascii")) + [0xF7]
