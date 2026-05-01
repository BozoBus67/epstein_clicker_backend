from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from db.client import supabase
from services.auth import require_user
from data.scrolls import MASTERY_SCROLLS

router = APIRouter()

# Valid bot IDs are every mastery_scroll_* plus the special "epstein" boss bot.
VALID_BOT_IDS = set(list(MASTERY_SCROLLS.keys()) + ["epstein"])


class MarkBotBeatenRequest(BaseModel):
  scroll_id: str


@router.post("/chess/mark_bot_beaten")
def mark_chess_bot_beaten(body: MarkBotBeatenRequest, user=Depends(require_user)):
  if body.scroll_id not in VALID_BOT_IDS:
    raise HTTPException(status_code=400, detail=f"Unknown chess bot id '{body.scroll_id}'")

  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  beaten = pgd.get("chess_beaten_bots", [])
  if body.scroll_id not in beaten:
    beaten.append(body.scroll_id)
    pgd["chess_beaten_bots"] = beaten
    supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"chess_beaten_bots": pgd.get("chess_beaten_bots", [])}
