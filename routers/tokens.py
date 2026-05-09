import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from db.client import supabase
from services.auth import require_user

router = APIRouter()

# All three checkin endpoints fire from the client on mount in parallel and
# do read-modify-write on the same `premium_game_data` JSON blob. Without
# serialization the last writer wins and the other two grants vanish. A
# per-user lock makes the trio safe within this process.
_user_locks_master = threading.Lock()
_user_locks: dict[str, threading.Lock] = {}

def _user_lock(user_id):
  with _user_locks_master:
    lock = _user_locks.get(user_id)
    if lock is None:
      lock = threading.Lock()
      _user_locks[user_id] = lock
    return lock

def _now():
  return datetime.now(timezone.utc)

def _parse_ts(ts):
  if ts is None:
    return None
  return datetime.fromisoformat(ts)

@router.post("/daily_checkin")
def daily_checkin(user=Depends(require_user)):
  with _user_lock(user.id):
    result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
    pgd = result.data["premium_game_data"]

    today = _now().date().isoformat()
    last = pgd["last_login_date"]
    streak = pgd["login_streak"]

    if last == today:
      return {"already_checked_in": True, "streak": streak, "premium_game_data": pgd}

    yesterday = (_now().date() - timedelta(days=1)).isoformat()
    streak = streak + 1 if last == yesterday else 1
    tokens_granted = streak * 25

    pgd["tokens"] = pgd["tokens"] + tokens_granted
    pgd["last_login_date"] = today
    pgd["login_streak"] = streak

    supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()

    return {"already_checked_in": False, "streak": streak, "tokens_granted": tokens_granted, "premium_game_data": pgd}

@router.post("/hourly_checkin")
def hourly_checkin(user=Depends(require_user)):
  with _user_lock(user.id):
    result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
    pgd = result.data["premium_game_data"]

    now = _now()
    last = _parse_ts(pgd["last_hourly_claim"])
    streak = pgd["hourly_streak"]

    if last is not None and (now - last) < timedelta(hours=1):
      return {"already_checked_in": True, "streak": streak, "premium_game_data": pgd}

    streak = streak + 1 if (last is not None and (now - last) < timedelta(hours=2)) else 1
    tokens_granted = streak * 5

    pgd["tokens"] = pgd["tokens"] + tokens_granted
    pgd["last_hourly_claim"] = now.isoformat()
    pgd["hourly_streak"] = streak

    supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()

    return {"already_checked_in": False, "streak": streak, "tokens_granted": tokens_granted, "premium_game_data": pgd}

@router.post("/fivemin_checkin")
def fivemin_checkin(user=Depends(require_user)):
  with _user_lock(user.id):
    result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
    pgd = result.data["premium_game_data"]

    now = _now()
    last = _parse_ts(pgd["last_5min_claim"])
    streak = pgd["fivemin_streak"]

    if last is not None and (now - last) < timedelta(minutes=5):
      return {"already_checked_in": True, "streak": streak, "premium_game_data": pgd}

    streak = streak + 1 if (last is not None and (now - last) < timedelta(minutes=10)) else 1
    tokens_granted = streak * 1

    pgd["tokens"] = pgd["tokens"] + tokens_granted
    pgd["last_5min_claim"] = now.isoformat()
    pgd["fivemin_streak"] = streak

    supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()

    return {"already_checked_in": False, "streak": streak, "tokens_granted": tokens_granted, "premium_game_data": pgd}
