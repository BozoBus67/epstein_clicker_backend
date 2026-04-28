from fastapi import APIRouter, Depends
from utils import require_user, generate_slot_sequence
from initializations_and_declarations.scroll_declarations import MASTERY_SCROLLS
from constants.constants import SLOT_REEL_LENGTH

router = APIRouter()

@router.post("/spin")
def spin(user=Depends(require_user)):
    return {"sequences": generate_slot_sequence(count=len(MASTERY_SCROLLS), length=SLOT_REEL_LENGTH)}
