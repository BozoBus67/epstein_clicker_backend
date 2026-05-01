import pytest

from services.slots import compute_wins

REWARDS = {2: 1, 3: 3, 4: 10, 5: 100}
SCROLL_KEYS = [f"mastery_scroll_{i}" for i in range(1, 25)]
SUBSET = [10, 11, 12, 13, 14, 15]

S = lambda i: SCROLL_KEYS[SUBSET[i]]  # readable shortcut: S(0) == "mastery_scroll_11"


@pytest.mark.parametrize("name, results, expected_wins", [
  (
    "no matches → no wins",
    [0, 1, 2, 3, 4],
    [],
  ),
  (
    "one pair → one win at amount 1",
    [0, 0, 1, 2, 3],
    [{"scroll_id": S(0), "amount": REWARDS[2]}],
  ),
  (
    "two pairs → both win (regression for the originally-reported bug)",
    [0, 0, 1, 1, 2],
    [
      {"scroll_id": S(0), "amount": REWARDS[2]},
      {"scroll_id": S(1), "amount": REWARDS[2]},
    ],
  ),
  (
    "triple → one win at amount 3",
    [0, 0, 0, 1, 2],
    [{"scroll_id": S(0), "amount": REWARDS[3]}],
  ),
  (
    "full house (triple + pair) → both win",
    [0, 0, 0, 1, 1],
    [
      {"scroll_id": S(0), "amount": REWARDS[3]},
      {"scroll_id": S(1), "amount": REWARDS[2]},
    ],
  ),
  (
    "four of a kind + singleton → one win at amount 10",
    [0, 0, 0, 0, 1],
    [{"scroll_id": S(0), "amount": REWARDS[4]}],
  ),
  (
    "five of a kind (jackpot) → one win at amount 100",
    [0, 0, 0, 0, 0],
    [{"scroll_id": S(0), "amount": REWARDS[5]}],
  ),
])
def test_compute_wins(name, results, expected_wins):
  wins = compute_wins(results, SUBSET, SCROLL_KEYS, REWARDS)
  # Order isn't part of the contract — compare as sets of frozen items.
  assert _normalize(wins) == _normalize(expected_wins), name


def _normalize(wins):
  return sorted((w["scroll_id"], w["amount"]) for w in wins)
