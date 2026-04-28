from fastapi import APIRouter
from data.scrolls import MASTERY_SCROLLS

router = APIRouter()

@router.get("/get_scroll_metadata")
def get_scroll_metadata():
  return MASTERY_SCROLLS
