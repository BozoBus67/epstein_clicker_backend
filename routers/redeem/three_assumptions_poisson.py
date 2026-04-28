import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from utils import require_user, add_tokens

router = APIRouter()

REWARD = 100

ANSWER_1 = "at any given moment an event may happen"
ANSWER_2 = "law of unconcious statician"
ANSWER_3A = "your mom fat and gay theorem"
ANSWER_3B = "ur mom fat and fat theorem"

FIXED_ANSWERS = {ANSWER_1, ANSWER_2}
VALID_ANSWER_SETS = [
  FIXED_ANSWERS | {ANSWER_3A},
  FIXED_ANSWERS | {ANSWER_3B},
]

def normalize(s: str) -> str:
  return re.sub(r"[,.\u2019']+", "", s.strip().lower())

class ThreeAssumptionsRequest(BaseModel):
  answer_1: str
  answer_2: str
  answer_3: str

@router.post("/three_assumptions_poisson")
def three_assumptions_poisson(body: ThreeAssumptionsRequest, user=Depends(require_user)):
  submitted = {normalize(body.answer_1), normalize(body.answer_2), normalize(body.answer_3)}
  if submitted not in VALID_ANSWER_SETS:
    return {"correct": False}
  add_tokens(user.id, REWARD)
  return {"correct": True, "tokens_awarded": REWARD}
