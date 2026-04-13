from fastapi import APIRouter
from initializations_and_declarations.scroll_declarations import MASTERY_SCROLLS

router = APIRouter()

@router.get("/get_scroll_metadata")
def get_scroll_metadata():
  return MASTERY_SCROLLS