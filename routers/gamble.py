from fastapi import APIRouter, Depends
from utils import require_user, generate_slot_sequence
from initializations_and_declarations.scroll_declarations import MASTERY_SCROLLS

router = APIRouter()

REEL_LENGTH = 10

@router.post("/spin")
def spin(user=Depends(require_user)):
    return {"sequences": generate_slot_sequence(count=len(MASTERY_SCROLLS), length=REEL_LENGTH)}
