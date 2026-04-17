from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
from initializations_and_declarations.db_initialization import supabase
from utils import require_user

router = APIRouter()

@router.post("/daily_checkin")
def daily_checkin(user=Depends(require_user)):
  result = supabase.table("User_Login_Data").select(
    "premium_game_data"
  ).eq("id", user.id).single().execute()
  pgd = result.data["premium_game_data"]

  today = datetime.now(timezone.utc).date().isoformat()
  last = pgd.get("last_login_date")
  streak = pgd["login_streak"]
  tokens = pgd["tokens"]

  if last == today:
    return {"already_checked_in": True, "tokens": tokens, "streak": streak}

  yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
  streak = streak + 1 if last == yesterday else 1
  tokens_to_grant = streak

  pgd["tokens"] = tokens + tokens_to_grant
  pgd["last_login_date"] = today
  pgd["login_streak"] = streak

  supabase.table("User_Login_Data").update({
    "premium_game_data": pgd
  }).eq("id", user.id).execute()

  return {
    "already_checked_in": False,
    "tokens": pgd["tokens"],
    "streak": streak,
    "tokens_granted": tokens_to_grant,
  }