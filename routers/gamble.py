import random

from fastapi import APIRouter, Depends

from constants.constants import SLOT_ALPHABET_SIZE, SLOT_REEL_LENGTH
from data.scrolls import MASTERY_SCROLLS
from services.analytics import capture as analytics_capture
from services.auth import require_user
from services.scrolls import increase_mastery_scroll
from services.slots import compute_wins, generate_slot_sequence
from services.tokens import spend_tokens

router = APIRouter()

# Slot machine config. The reel renders as 5 wheels; on stop, every value that
# appears >=2 times is a win, with reward scaling by group size (REWARDS).
SPIN_COST = 1
REEL_COUNT = 5
SCROLL_KEYS = list(MASTERY_SCROLLS.keys())
REWARDS = {2: 1, 3: 3, 4: 10, 5: 100}

# Roulette config. One wheel, one slot landed on, one scroll awarded.
ROULETTE_SPIN_COST = 1
ROULETTE_REWARD_AMOUNT = 1

@router.post("/spin")
def spin(user=Depends(require_user)):
  tokens_remaining = spend_tokens(user.id, SPIN_COST)

  subset_indices = random.sample(range(len(SCROLL_KEYS)), SLOT_ALPHABET_SIZE)
  sequences = generate_slot_sequence(count=SLOT_ALPHABET_SIZE, length=SLOT_REEL_LENGTH, rows=REEL_COUNT)

  results = [seq[-1] for seq in sequences]
  wins = compute_wins(results, subset_indices, SCROLL_KEYS, REWARDS)
  for win in wins:
    increase_mastery_scroll(user.id, win["scroll_id"], win["amount"])

  analytics_capture(distinct_id=user.id, event="gamble_spin")

  return {"sequences": sequences, "subset_indices": subset_indices, "tokens_remaining": tokens_remaining, "wins": wins}

@router.post("/roulette_spin")
def roulette_spin(user=Depends(require_user)):
  tokens_remaining = spend_tokens(user.id, ROULETTE_SPIN_COST)
  scroll_id = random.choice(SCROLL_KEYS)
  increase_mastery_scroll(user.id, scroll_id, ROULETTE_REWARD_AMOUNT)

  analytics_capture(distinct_id=user.id, event="roulette_spin")

  return {"tokens_remaining": tokens_remaining, "scroll_id": scroll_id}
