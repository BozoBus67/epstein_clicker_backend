from fastapi import APIRouter
from initializations_and_declarations.account_tier_declarations import ACCOUNT_TIERS

router = APIRouter()

@router.get("/account_tiers")
def get_account_tiers():
  return ACCOUNT_TIERS