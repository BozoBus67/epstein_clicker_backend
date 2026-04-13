from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, date, timedelta, timezone
from initializations_and_declarations.db_initialization import supabase
from utils import require_user

router = APIRouter()

class UsernameRequest(BaseModel):
  username: str

class SpendRequest(BaseModel):
  username: str
  amount: int

@router.post("/daily_checkin")
def daily_checkin(body: UsernameRequest):
  user = require_user(body.username)
  pgd = user["premium_game_data"]

  today = datetime.now(timezone.utc).date().isoformat()
  last = pgd["last_login_date"]
  streak = pgd["login_streak"]
  tokens = pgd["premium_tokens"]

  if last == today:
    return {"already_checked_in": True, "tokens": tokens, "streak": streak}

  yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
  streak = streak + 1 if last == yesterday else 1
  tokens_to_grant = streak

  pgd["premium_tokens"] = tokens + tokens_to_grant
  pgd["last_login_date"] = today
  pgd["login_streak"] = streak

  supabase.table("User_Login_Data").update({
    "premium_game_data": pgd
  }).eq("username", body.username).execute()

  return {
    "already_checked_in": False,
    "tokens": tokens + tokens_to_grant,
    "streak": streak,
    "tokens_granted": tokens_to_grant,
  }

@router.post("/spend_tokens")
def spend_tokens(body: SpendRequest):
  user = require_user(body.username)
  pgd = user["premium_game_data"]

  tokens = pgd["premium_tokens"]
  if tokens < body.amount:
    raise HTTPException(status_code=400, detail="Not enough tokens")

  pgd["premium_tokens"] = tokens - body.amount

  supabase.table("User_Login_Data").update({
    "premium_game_data": pgd
  }).eq("username", body.username).execute()

  return {"tokens": pgd["premium_tokens"]}