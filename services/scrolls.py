import random
from fastapi import HTTPException
from db.client import supabase
from data.scrolls import SCROLL_TIERS, MASTERY_SCROLLS

def increase_mastery_scroll(user_uuid: str, scroll_id: str, amount: int = 1):
  if scroll_id not in MASTERY_SCROLLS:
    raise HTTPException(status_code=500, detail=f"Unknown scroll_id '{scroll_id}' (not in MASTERY_SCROLLS)")
  user = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user_uuid).single().execute().data
  pgd = user["premium_game_data"]
  if scroll_id not in pgd:
    raise HTTPException(status_code=500, detail=f"User {user_uuid} premium_game_data is missing scroll_id '{scroll_id}'. Account predates this scroll — needs data migration.")
  pgd[scroll_id] = pgd[scroll_id] + amount
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user_uuid).execute()

def get_scroll_tier(count: int) -> int:
  tier = 0
  for t in SCROLL_TIERS:
    if count >= t["min"]:
      tier = t["tier"]
  return tier

def get_random_scroll_id() -> str:
  return random.choice(list(MASTERY_SCROLLS.keys()))
