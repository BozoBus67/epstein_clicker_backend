from fastapi import APIRouter
from data.account_tiers import ACCOUNT_TIERS

router = APIRouter()

@router.get("/account_tiers")
def get_account_tiers():
  return ACCOUNT_TIERS
