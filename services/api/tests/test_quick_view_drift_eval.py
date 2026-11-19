"""The Quick View drift eval's planting and scoring (slice 4g). No model calls."""

from evals.quick_view_drift import PLANTS, Verdict, plant, score

QUICK = [
    "Soften the onion in the oil over medium heat for 8 minutes.",
    "Spread in a dish and top with the cheese.",
    "Bake at 180°C for 35–40 minutes until golden.",
]


def test_each_plant_changes_the_quick_steps_and_says_how() -> None:
    for kind in PLANTS:
        planted = plant(kind, QUICK)
        assert planted is not None, kind
        steps, note = planted
        assert steps != QUICK and note, kind


def test_plants_change_what_they_say() -> None:
    assert plant("time", QUICK) == (
        [*QUICK[:2], QUICK[2].replace("35–40 minutes", "1 minute")],
        "time: '35–40 minutes' became '1 minute'",
    )
    temp = plant("temperature", QUICK)
    assert temp is not None and "240°C" in temp[0][2]
    dropped = plant("dropped", QUICK)
    assert dropped is not None and len(dropped[0]) == 2
    assert plant("method", ["Mix the dressing."]) is None  # nothing to change: skipped


def test_scoring_counts_catches_and_false_alarms() -> None:
    verdicts = {
        "a": Verdict(same_cooking=False, differences=["time"]),
        "b": Verdict(same_cooking=True, differences=[]),
        "c": Verdict(same_cooking=False, differences=["order"]),
        "d": None,
    }
    planted = {"a": "time", "b": "order", "c": None, "d": None}
    s = score(planted, verdicts)
    assert (s.planted, s.caught, s.sound, s.false_alarms, s.no_answer) == (2, 1, 2, 1, 1)
