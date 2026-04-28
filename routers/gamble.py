from fastapi import APIRouter, Depends
from utils import require_user, generate_slot_sequence, spend_tokens
from initializations_and_declarations.scroll_declarations import MASTERY_SCROLLS
from constants.constants import SLOT_REEL_LENGTH

router = APIRouter()

SPIN_COST = 1

@router.post("/spin")
def spin(user=Depends(require_user)):
    tokens_remaining = spend_tokens(user.id, SPIN_COST)
    return {"sequences": generate_slot_sequence(count=len(MASTERY_SCROLLS), length=SLOT_REEL_LENGTH), "tokens_remaining": tokens_remaining}
