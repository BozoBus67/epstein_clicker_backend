from fastapi import HTTPException

from db.client import supabase

def add_cookies(user_uuid: str, amount: int):
  user = supabase.table("User_Login_Data").select("game_data").eq("id", user_uuid).single().execute().data
  gd = user["game_data"]
  gd["quantity"] = gd["quantity"] + amount
  supabase.table("User_Login_Data").update({"game_data": gd}).eq("id", user_uuid).execute()

def spend_cookies(user_uuid: str, amount: int):
  user = supabase.table("User_Login_Data").select("game_data").eq("id", user_uuid).single().execute().data
  gd = user["game_data"]
  if gd["quantity"] < amount:
    raise HTTPException(status_code=400, detail="Not enough cookies")
  gd["quantity"] = gd["quantity"] - amount
  supabase.table("User_Login_Data").update({"game_data": gd}).eq("id", user_uuid).execute()
