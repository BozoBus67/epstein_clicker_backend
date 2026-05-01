from fastapi import APIRouter, Depends

from db.client import supabase
from services.auth import require_user

router = APIRouter()

REWARD = 25

# One-time honour-system claim: the frontend gates this behind a checkbox
# ("I solemnly swear I sent this to at least 2 other people..."), the backend
# just records that the claim has happened and grants tokens. There's no way
# to verify the user actually told anyone — that's intentional, the modal is
# basically a fun honour-system referral promise.
@router.post("/promotion_oath")
def promotion_oath(user=Depends(require_user)):
  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  if pgd["redeemed"].get("promotion_oath"):
    return {"already_redeemed": True}
  pgd["tokens"] = pgd["tokens"] + REWARD
  pgd["redeemed"]["promotion_oath"] = True
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"already_redeemed": False, "tokens_awarded": REWARD}
