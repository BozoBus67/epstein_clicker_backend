from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date, timedelta, timezone
from db_initialization import supabase
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

  today = date.today(timezone.utc).isoformat()
  last = user["last_login_date"]
  streak = user["login_streak"]
  tokens = user["premium_tokens"]

  if last == today:
    return {"already_checked_in": True, "tokens": tokens, "streak": streak}

  yesterday = (date.today(timezone.utc) - timedelta(days=1)).isoformat()
  streak = streak + 1 if last == yesterday else 1
  tokens_to_grant = streak

  supabase.table("User_Login_Data").update({
    "premium_tokens": tokens + tokens_to_grant,
    "last_login_date": today,
    "login_streak": streak
  }).eq("username", body.username).execute()

  return {
    "already_checked_in": False,
    "tokens": tokens + tokens_to_grant,
    "streak": streak,
    "tokens_granted": tokens_to_grant
  }

@router.post("/spend_tokens")
def spend_tokens(body: SpendRequest):
  user = require_user(body.username)

  tokens = user["premium_tokens"]
  if tokens < body.amount:
    raise HTTPException(status_code=400, detail="Not enough tokens")

  new_balance = tokens - body.amount

  supabase.table("User_Login_Data").update({
    "premium_tokens": new_balance
  }).eq("username", body.username).execute()

  return {"tokens": new_balance}