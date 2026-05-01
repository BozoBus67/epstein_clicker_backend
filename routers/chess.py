from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from data.scrolls import MASTERY_SCROLLS
from db.client import supabase
from services.auth import require_user

router = APIRouter()

# A chess bot's id is either a mastery_scroll_* string or the special "epstein"
# boss id. The naming is "bot_id" rather than "scroll_id" because the value
# isn't always a scroll — Epstein in particular isn't.
VALID_BOT_IDS = set(list(MASTERY_SCROLLS.keys()) + ["epstein"])


class MarkBotBeatenRequest(BaseModel):
  bot_id: str


@router.post("/chess/mark_bot_beaten")
def mark_chess_bot_beaten(body: MarkBotBeatenRequest, user=Depends(require_user)):
  if body.bot_id not in VALID_BOT_IDS:
    raise HTTPException(status_code=400, detail=f"Unknown chess bot id '{body.bot_id}'")

  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  beaten = pgd.get("chess_beaten_bots", [])
  if body.bot_id not in beaten:
    beaten.append(body.bot_id)
    pgd["chess_beaten_bots"] = beaten
    supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"chess_beaten_bots": pgd.get("chess_beaten_bots", [])}
