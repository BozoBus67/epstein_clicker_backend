from fastapi import APIRouter, Depends
from pydantic import BaseModel

from db.client import supabase
from services.analytics import capture as analytics_capture
from services.auth import require_user

router = APIRouter()

REWARD = 100

# Faithful to the meme: the comma in the first answer is required, and the
# third answer must use "ur" — "your" is rejected. We only normalize case +
# trim whitespace; punctuation matters.
VALID_ANSWERS = {
  "at any given moment, an event may happen",
  "law of unconcious statician",
  "ur mom fat and gay theorem",
}


def normalize(s: str) -> str:
  return s.strip().lower()


class ThreeAssumptionsRequest(BaseModel):
  answer_1: str
  answer_2: str
  answer_3: str


@router.post("/three_assumptions_poisson")
def three_assumptions_poisson(body: ThreeAssumptionsRequest, user=Depends(require_user)):
  submitted = {normalize(body.answer_1), normalize(body.answer_2), normalize(body.answer_3)}
  if submitted != VALID_ANSWERS:
    return {"correct": False}
  # Track every correct submission, not just the first one — gives us a sense
  # of how many people figured out the meme. Already-redeemed retries still
  # count as "they got it right."
  analytics_capture(distinct_id=user.id, event="poisson_correct")
  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  if pgd["redeemed"].get("poisson"):
    return {"correct": True, "already_redeemed": True}
  pgd["tokens"] = pgd["tokens"] + REWARD
  pgd["redeemed"]["poisson"] = True
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"correct": True, "already_redeemed": False, "tokens_awarded": REWARD}
