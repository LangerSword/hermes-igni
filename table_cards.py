"""Card data for the two Table modes.

Everything here is original: names, stats and the compact rulesets are written
for this plugin. Gwent mode borrows the *shape* of row warfare (weather, spies,
horns, scorch); Arena borrows the *shape* of a mana duel (taunts, charge,
divine shield). Neither is a port of a commercial game, and no asset from one
is used.
"""

from __future__ import annotations

GWENT_FACTIONS = {
    "northern": "Northern Realms",
    "nilfgaard": "Nilfgaard",
}


def _g(key, name, kind, row, strength=0, copies=1, text=""):
    return {
        "key": key,
        "name": name,
        "kind": kind,
        "row": row,
        "strength": strength,
        "copies": copies,
        "text": text,
    }


# Each pool below sums to exactly 22 cards; the engine deals 10 and keeps the
# rest as the draw pile. Weather, horn, clear and scorch are the only specials.
GWENT_POOLS = {
    "northern": [
        _g("blue_stripes", "Blue Stripes Commando", "unit", "melee", 4, 3),
        _g("redanian_elite", "Redanian Elite", "unit", "melee", 5, 2),
        _g("poor_infantry", "Poor Infantry", "unit", "melee", 1, 1),
        _g("aedirnian_mauler", "Aedirnian Mauler", "unit", "melee", 4, 2),
        _g("crinfrid_reavers", "Crinfrid Reavers", "unit", "ranged", 5, 2),
        _g("ballista", "Ballista", "unit", "siege", 6, 2),
        _g("catapult", "Catapult", "unit", "siege", 8, 1),
        _g("trebuchet", "Trebuchet", "unit", "siege", 6, 1),
        _g("geralt", "Geralt of Rivia", "hero", "melee", 15, 1,
           "Hero: immune to weather."),
        _g("philippa", "Philippa Eilhart", "hero", "ranged", 10, 1,
           "Hero: immune to weather."),
        _g("vernon", "Vernon Roche", "hero", "melee", 5, 1,
           "Hero: immune to weather."),
        _g("dijkstra", "Sigismund Dijkstra", "spy", "melee", 4, 1,
           "Spy: joins the enemy row, you draw 2."),
        _g("horn", "Commander's Horn", "horn", "row", 0, 1,
           "Special: double one of your rows."),
        _g("frost", "Biting Frost", "weather", "melee", 0, 1,
           "Weather: melee units are 1 (heroes exempt)."),
        _g("clear", "Clear Weather", "clear", "weather", 0, 1,
           "Special: remove all weather."),
        _g("scorch", "Scorch", "scorch", "board", 0, 1,
           "Special: destroy the strongest non-hero unit(s) on the board."),
    ],
    "nilfgaard": [
        _g("impera", "Impera Brigade", "unit", "melee", 4, 3),
        _g("alba_pikemen", "Alba Pikemen", "unit", "melee", 3, 2),
        _g("nausicaa", "Nausicaa Cavalry Rider", "unit", "melee", 3, 2),
        _g("black_archer", "Black Infantry Archer", "unit", "ranged", 6, 2),
        _g("etolian", "Etolian Auxiliaries", "unit", "ranged", 2, 2),
        _g("mangonel", "Mangonel", "unit", "siege", 6, 2),
        _g("scorpion", "Scorpion", "unit", "siege", 6, 1),
        _g("letho", "Letho of Gulet", "hero", "melee", 7, 1,
           "Hero: immune to weather."),
        _g("tibor", "Tibor Eggebracht", "hero", "ranged", 10, 1,
           "Hero: immune to weather."),
        _g("menno", "Menno Coehoorn", "hero", "siege", 10, 1,
           "Hero: immune to weather."),
        _g("shilard", "Shilard Fitz-Oesterlen", "spy", "ranged", 5, 1,
           "Spy: joins the enemy row, you draw 2."),
        _g("horn", "Commander's Horn", "horn", "row", 0, 1,
           "Special: double one of your rows."),
        _g("rain", "Torrential Rain", "weather", "siege", 0, 1,
           "Weather: siege units are 1 (heroes exempt)."),
        _g("fog", "Impenetrable Fog", "weather", "ranged", 0, 1,
           "Weather: ranged units are 1 (heroes exempt)."),
        _g("scorch", "Scorch", "scorch", "board", 0, 1,
           "Special: destroy the strongest non-hero unit(s) on the board."),
    ],
}

GWENT_WEATHER = {
    "frost": ("Biting Frost", "melee"),
    "fog": ("Impenetrable Fog", "ranged"),
    "rain": ("Torrential Rain", "siege"),
}

GWENT_ROWS = ("melee", "ranged", "siege")


def build_gwent_deck(faction: str) -> list[dict]:
    """Expand a faction pool into its 22 physical cards."""
    if faction not in GWENT_POOLS:
        raise ValueError(
            f"unknown faction {faction!r}; choose one of {', '.join(GWENT_POOLS)}"
        )
    deck: list[dict] = []
    for spec in GWENT_POOLS[faction]:
        for _ in range(int(spec["copies"])):
            deck.append({k: v for k, v in spec.items() if k != "copies"})
    return deck


# ---------------------------------------------------------------- Arena ----

ARENA_DECKS = {
    "vanguard": "Vanguard",
    "syndicate": "Syndicate",
}


def _a(
    key,
    name,
    kind,
    cost,
    copies=1,
    attack=0,
    health=0,
    taunt=False,
    charge=False,
    shield=False,
    battlecry=None,
    spell=None,
    text="",
):
    return {
        "key": key,
        "name": name,
        "kind": kind,
        "cost": cost,
        "copies": copies,
        "attack": attack,
        "health": health,
        "taunt": taunt,
        "charge": charge,
        "shield": shield,
        "battlecry": battlecry,
        "spell": spell,
        "text": text,
    }


# Twenty cards each, built for a short duel. Curves: cheap bodies, two taunts,
# one charge threat, one shield body, four spells.
ARENA_POOLS = {
    "vanguard": [
        _a("emberling", "Emberling", "minion", 1, 1, 1, 2),
        _a("shieldbearer", "Shieldbearer", "minion", 2, 2, 1, 4, taunt=True),
        _a("ash_hound", "Ash Hound", "minion", 2, 1, 3, 2),
        _a("cinder_guard", "Cinder Guard", "minion", 3, 2, 2, 4, taunt=True),
        _a("blade_dancer", "Blade Dancer", "minion", 3, 2, 3, 3),
        _a("sunspear", "Sunspear", "minion", 4, 2, 4, 3, charge=True),
        _a("bulwark", "Bulwark Golem", "minion", 4, 1, 3, 6, taunt=True),
        _a("pyre_mage", "Pyre Mage", "minion", 5, 2, 4, 5,
           battlecry={"type": "aoe", "amount": 1}),
        _a("dawnbreaker", "Dawnbreaker", "minion", 6, 1, 6, 6, shield=True),
        _a("colossus", "Colossus", "minion", 7, 1, 7, 7, taunt=True),
        _a("ember_bolt", "Ember Bolt", "spell", 2, 2,
           spell={"type": "damage", "amount": 3}),
        _a("reinforce", "Reinforce", "spell", 3, 1,
           spell={"type": "draw", "amount": 2}),
        _a("sunrise", "Sunrise", "spell", 4, 1,
           spell={"type": "heal", "amount": 8}),
        _a("cleansing_flame", "Cleansing Flame", "spell", 5, 1,
           spell={"type": "aoe", "amount": 2}),
    ],
    "syndicate": [
        _a("grunt", "Syndicate Grunt", "minion", 1, 2, 2, 1),
        _a("nightblade", "Nightblade", "minion", 2, 2, 2, 3),
        _a("boneguard", "Boneguard", "minion", 2, 2, 1, 4, taunt=True),
        _a("cutthroat", "Cutthroat", "minion", 3, 2, 4, 2),
        _a("warden", "Warden", "minion", 3, 2, 2, 5, taunt=True),
        _a("hexer", "Hexer", "minion", 4, 1, 4, 4,
           battlecry={"type": "draw", "amount": 1}),
        _a("ravager", "Ravager", "minion", 4, 1, 5, 2, charge=True),
        _a("bloodmoon_priest", "Bloodmoon Priest", "minion", 5, 1, 4, 5,
           battlecry={"type": "aoe", "amount": 1}),
        _a("ironjaw", "Ironjaw", "minion", 6, 1, 6, 6, taunt=True),
        _a("dreadnought", "Dreadnought", "minion", 7, 1, 8, 8),
        _a("shadow_bolt", "Shadow Bolt", "spell", 2, 2,
           spell={"type": "damage", "amount": 3}),
        _a("dark_pact", "Dark Pact", "spell", 3, 1,
           spell={"type": "draw", "amount": 2}),
        _a("blood_rite", "Blood Rite", "spell", 4, 1,
           spell={"type": "heal", "amount": 8}),
        _a("plague", "Plague", "spell", 5, 1,
           spell={"type": "aoe", "amount": 2}),
    ],
}


def build_arena_deck(deck_name: str) -> list[dict]:
    if deck_name not in ARENA_POOLS:
        raise ValueError(
            f"unknown deck {deck_name!r}; choose one of {', '.join(ARENA_POOLS)}"
        )
    deck: list[dict] = []
    for spec in ARENA_POOLS[deck_name]:
        for _ in range(int(spec["copies"])):
            deck.append({k: v for k, v in spec.items() if k != "copies"})
    return deck


# Card key -> pixel-art stem in art/<stem>.webp. Several cards share an
# archetype print; the frame, title and stats keep each card distinct.
ART_BY_KEY = {
    # Gwent: Ashen Crown
    "blue_stripes": "gwent_infantry",
    "redanian_elite": "gwent_infantry",
    "poor_infantry": "gwent_infantry",
    "aedirnian_mauler": "gwent_infantry",
    "crinfrid_reavers": "gwent_archer",
    "ballista": "gwent_siege",
    "catapult": "gwent_siege",
    "trebuchet": "gwent_siege",
    "geralt": "gwent_hero_ash",
    "philippa": "gwent_hero_lady",
    "vernon": "gwent_hero_ash",
    "dijkstra": "gwent_spy",
    # Gwent: Obsidian Court
    "impera": "gwent_infantry",
    "alba_pikemen": "gwent_infantry",
    "nausicaa": "gwent_infantry",
    "black_archer": "gwent_archer",
    "etolian": "gwent_archer",
    "mangonel": "gwent_siege",
    "scorpion": "gwent_siege",
    "letho": "gwent_hero_obsidian",
    "tibor": "gwent_hero_obsidian",
    "menno": "gwent_hero_obsidian",
    "shilard": "gwent_spy",
    # Gwent specials
    "horn": "gwent_horn",
    "frost": "weather_frost",
    "fog": "weather_fog",
    "rain": "weather_rain",
    "clear": "weather_clear",
    "scorch": "gwent_scorch",
    # Arena: Vanguard
    "emberling": "arena_duelist",
    "shieldbearer": "arena_guard",
    "ash_hound": "arena_duelist",
    "cinder_guard": "arena_guard",
    "blade_dancer": "arena_duelist",
    "sunspear": "arena_duelist",
    "bulwark": "arena_guard",
    "pyre_mage": "arena_mage",
    "dawnbreaker": "arena_giant",
    "colossus": "arena_giant",
    "ember_bolt": "spell_bolt",
    "reinforce": "spell_draw",
    "sunrise": "spell_heal",
    "cleansing_flame": "gwent_scorch",
    # Arena: Syndicate
    "grunt": "arena_duelist",
    "nightblade": "arena_duelist",
    "boneguard": "arena_guard",
    "cutthroat": "arena_duelist",
    "warden": "arena_guard",
    "hexer": "arena_mage",
    "ravager": "arena_duelist",
    "bloodmoon_priest": "arena_mage",
    "ironjaw": "arena_guard",
    "dreadnought": "arena_giant",
    "shadow_bolt": "spell_bolt",
    "dark_pact": "spell_draw",
    "blood_rite": "spell_heal",
    "plague": "gwent_scorch",
}

ART_BACK = "card_back"


GWENT_RULES = """\
GWENT — best of three, one card per turn.

Goal: win two rounds. A round ends when both sides pass. Highest row total
wins it; a tie awards the round to both sides.
Rows: melee, ranged, siege. A unit's strength counts on its own row.
Weather sets every non-hero unit on one row to 1, for BOTH sides; Clear
Weather removes all weather. Commander's Horn doubles one of your rows.
Spies join the enemy's row but draw you 2 cards. Scorch destroys the
strongest non-hero unit(s) on the board — both sides, so mind your own.
Heroes are immune to weather. Hands and the draw pile carry over between
rounds; the board, weather and horns are cleared.

Moves: play <hand#> [row] for a horn · pass · concede."""

ARENA_RULES = """\
ARENA — a mana duel to zero health.

Each side has 30 health. Mana grows by one each turn, up to 10, and refills.
Draw one card at the start of your turn; an empty deck deals rising fatigue
damage. Minions may attack the turn after they arrive unless they have
Charge. Taunt minions must be attacked first. Divine Shield absorbs the
first damage. Battlecries fire when a minion is summoned.

Moves: play <hand#> [target] · attack <your board#> <enemy board#|hero> ·
end_turn · concede."""


def rules_for(mode: str) -> str:
    if mode == "gwent":
        return GWENT_RULES
    if mode == "arena":
        return ARENA_RULES
    raise ValueError(f"unknown mode {mode!r}; choose gwent or arena")


def card_list_for(mode: str, deck: str | None = None) -> str:
    """Human-readable pool listing, used by table_rules."""
    lines: list[str] = []
    if mode == "gwent":
        factions = [deck] if deck in GWENT_POOLS else list(GWENT_POOLS)
        for faction in factions:
            lines.append(f"{GWENT_FACTIONS[faction]}:")
            for spec in GWENT_POOLS[faction]:
                extra = f" — {spec['text']}" if spec["text"] else ""
                row = spec["row"] if spec["row"] not in ("row", "board", "weather") else "special"
                lines.append(
                    f"  {spec['name']} | {row} | {spec['strength']} | x{spec['copies']}{extra}"
                )
    elif mode == "arena":
        decks = [deck] if deck in ARENA_POOLS else list(ARENA_POOLS)
        for name in decks:
            lines.append(f"{ARENA_DECKS[name]} deck:")
            for spec in ARENA_POOLS[name]:
                if spec["kind"] == "minion":
                    flags = []
                    if spec["taunt"]:
                        flags.append("taunt")
                    if spec["charge"]:
                        flags.append("charge")
                    if spec["shield"]:
                        flags.append("shield")
                    flag = f" · {', '.join(flags)}" if flags else ""
                    lines.append(
                        f"  {spec['name']} | {spec['cost']} mana | "
                        f"{spec['attack']}/{spec['health']}{flag} | x{spec['copies']}"
                    )
                else:
                    lines.append(
                        f"  {spec['name']} | {spec['cost']} mana | spell: "
                        f"{spec['spell']['type']} {spec['spell']['amount']} | x{spec['copies']}"
                    )
    else:
        raise ValueError(f"unknown mode {mode!r}; choose gwent or arena")
    return "\n".join(lines)
