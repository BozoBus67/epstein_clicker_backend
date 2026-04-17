import random
from fastapi import HTTPException, Header
from initializations_and_declarations.db_initialization import supabase
from initializations_and_declarations.scroll_declarations import SCROLL_TIERS, MASTERY_SCROLLS
from initializations_and_declarations.game_data_declarations import INITIAL_GAME_DATA
import constants.constants as Constants

def require_user(authorization: str = Header(...)):
  if not authorization.startswith("Bearer "):
    raise HTTPException(status_code=401, detail="Invalid authorization header")
  token = authorization.removeprefix("Bearer ")
  try:
    result = supabase.auth.get_user(token)
  except Exception:
    raise HTTPException(status_code=401, detail="Invalid or expired token")
  if not result.user:
    raise HTTPException(status_code=401, detail="Invalid or expired token")
  return result.user

def migrate_game_data(saved: dict) -> dict:
  migrated = {**INITIAL_GAME_DATA, **saved}
  valid_building_keys = set(INITIAL_GAME_DATA["buildings"].keys())
  migrated["buildings"] = {
    key: saved.get("buildings", {}).get(key, 0)
    for key in valid_building_keys
  }
  migrated["version"] = INITIAL_GAME_DATA["version"]
  return migrated

def get_scroll_tier(count: int) -> int:
  tier = 0
  for t in SCROLL_TIERS:
    if count >= t["min"]:
      tier = t["tier"]
  return tier

def increase_mastery_scroll(user_uuid: str, scroll_id: str, amount: int = 1):
  user = (supabase.table("User_Login_Data")
    .select("premium_game_data")
    .eq("id", user_uuid)
    .single()
    .execute()
    .data)
  pgd = user["premium_game_data"]
  pgd[scroll_id] = pgd[scroll_id] + amount
  (supabase.table("User_Login_Data")
    .update({"premium_game_data": pgd})
    .eq("id", user_uuid)
    .execute())

def add_tokens(user_uuid: str, amount: int):
  user = (supabase.table("User_Login_Data")
    .select("premium_game_data")
    .eq("id", user_uuid)
    .single()
    .execute()
    .data)
  pgd = user["premium_game_data"]
  pgd["tokens"] = pgd["tokens"] + amount
  (supabase.table("User_Login_Data")
    .update({"premium_game_data": pgd})
    .eq("id", user_uuid)
    .execute())

def spend_tokens(user_uuid: str, amount: int):
  user = (supabase.table("User_Login_Data")
    .select("premium_game_data")
    .eq("id", user_uuid)
    .single()
    .execute()
    .data)
  pgd = user["premium_game_data"]
  if pgd["tokens"] < amount:
    raise HTTPException(status_code=400, detail="Not enough tokens")
  pgd["tokens"] = pgd["tokens"] - amount
  (supabase.table("User_Login_Data")
    .update({"premium_game_data": pgd})
    .eq("id", user_uuid)
    .execute())
  return pgd["tokens"]

def get_random_scroll_id() -> str:
  return random.choice(list(MASTERY_SCROLLS.keys()))

def generate_slot_sequence(length: int = 10) -> list[str]:
  return [''.join([str(random.randint(0, 9)) for _ in range(length)]) for _ in range(3)]