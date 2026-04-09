import random
from fastapi import HTTPException
from db_initialization import supabase
from scroll_declarations import SCROLL_TIERS, MASTERY_SCROLLS

def get_user(username: str):
  result = (supabase.table("User_Login_Data")
    .select("*")
    .eq("username", username)
    .single()
    .execute())
  return result.data

def require_user(username: str):
  user = get_user(username)
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  return user

def get_scroll_tier(count: int) -> int:
  tier = 0
  for t in SCROLL_TIERS:
    if count >= t["min"]:
      tier = t["tier"]
  return tier

def increase_mastery_scroll(user_uuid: str, scroll_id: str, amount: int = 1):
  user = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user_uuid).single().execute().data
  pgd = user["premium_game_data"]
  pgd[scroll_id] = pgd[scroll_id] + amount
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user_uuid).execute()

def get_random_scroll_id() -> str:
  return random.choice(list(MASTERY_SCROLLS.keys()))

def generate_slot_sequence(length: int = 10) -> list[str]:
  return [''.join([str(random.randint(0, 9)) for _ in range(length)]) for _ in range(3)]