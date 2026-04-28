from dotenv import load_dotenv
load_dotenv()

from db.client import supabase

USERNAME = "user1"
TOKENS = 9999

row = supabase.table("User_Login_Data").select("id, premium_game_data").eq("username", USERNAME).single().execute().data
pgd = row["premium_game_data"]
pgd["tokens"] = TOKENS
supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", row["id"]).execute()
print(f"Done — {USERNAME} now has {TOKENS} tokens")
