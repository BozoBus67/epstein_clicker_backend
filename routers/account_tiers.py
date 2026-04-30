from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from data.account_tiers import ACCOUNT_TIERS
from db.client import supabase
from services.auth import require_user

router = APIRouter()

TIER_ORDER = {t["id"]: i for i, t in enumerate(ACCOUNT_TIERS)}
TIER_PRICE = {t["id"]: t["token_price"] for t in ACCOUNT_TIERS}


@router.get("/account_tiers")
def get_account_tiers():
  return ACCOUNT_TIERS

class BuyTierRequest(BaseModel):
  tier_id: str

@router.post("/buy_account_tier")
def buy_account_tier(body: BuyTierRequest, user=Depends(require_user)):
  if body.tier_id not in TIER_ORDER:
    raise HTTPException(status_code=400, detail="Invalid tier")

  result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
  pgd = result.data["premium_game_data"]

  current_index = TIER_ORDER[pgd["account_tier"]]
  target_index = TIER_ORDER[body.tier_id]

  if target_index <= current_index:
    raise HTTPException(status_code=400, detail="You already have this tier or higher")
  if target_index != current_index + 1:
    raise HTTPException(status_code=400, detail="You must buy the previous tier first")

  price = TIER_PRICE[body.tier_id]
  if pgd["tokens"] < price:
    raise HTTPException(status_code=400, detail="Not enough tokens")

  pgd["tokens"] -= price
  pgd["account_tier"] = body.tier_id

  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()

  return {"premium_game_data": pgd}
