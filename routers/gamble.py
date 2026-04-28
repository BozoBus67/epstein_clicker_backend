from collections import Counter
from fastapi import APIRouter, Depends
from services.auth import require_user
from services.tokens import spend_tokens
from services.scrolls import increase_mastery_scroll
from services.slots import generate_slot_sequence
from data.scrolls import MASTERY_SCROLLS
from constants.constants import SLOT_REEL_LENGTH

router = APIRouter()

SPIN_COST = 1
REEL_COUNT = 5
SCROLL_KEYS = list(MASTERY_SCROLLS.keys())
REWARDS = {2: 1, 3: 3, 4: 10, 5: 100}

@router.post("/spin")
def spin(user=Depends(require_user)):
  tokens_remaining = spend_tokens(user.id, SPIN_COST)
  sequences = generate_slot_sequence(count=len(MASTERY_SCROLLS), length=SLOT_REEL_LENGTH, rows=REEL_COUNT)

  results = [seq[-1] for seq in sequences]
  most_common_val, most_common_count = Counter(results).most_common(1)[0]

  win = None
  if most_common_count >= 2:
    scroll_id = SCROLL_KEYS[most_common_val]
    amount = REWARDS[most_common_count]
    increase_mastery_scroll(user.id, scroll_id, amount)
    win = {"scroll_id": scroll_id, "amount": amount}

  return {"sequences": sequences, "tokens_remaining": tokens_remaining, "win": win}
