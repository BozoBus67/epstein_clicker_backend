from fastapi import HTTPException
from db.client import supabase

def add_tokens(user_uuid: str, amount: int):
  user = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user_uuid).single().execute().data
  pgd = user["premium_game_data"]
  pgd["tokens"] = pgd["tokens"] + amount
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user_uuid).execute()

def spend_tokens(user_uuid: str, amount: int) -> int:
  user = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user_uuid).single().execute().data
  pgd = user["premium_game_data"]
  if pgd["tokens"] < amount:
    raise HTTPException(status_code=400, detail="Not enough tokens")
  pgd["tokens"] = pgd["tokens"] - amount
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user_uuid).execute()
  return pgd["tokens"]
