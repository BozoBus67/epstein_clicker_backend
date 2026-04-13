from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from initializations_and_declarations.db_initialization import supabase
from initializations_and_declarations.premium_game_data_declarations import INITIAL_PREMIUM_GAME_DATA
from initializations_and_declarations.game_data_declarations import INITIAL_GAME_DATA

router = APIRouter()

class SignUpRequest(BaseModel):
  email: str
  username: str
  password: str

@router.post("/signup")
def signup(body: SignUpRequest):
  try:
    result = supabase.table("User_Login_Data").insert({
      "email": body.email,
      "username": body.username,
      "password": body.password,
      "game_data": INITIAL_GAME_DATA,
      "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
    }).execute()
  except Exception:
    raise HTTPException(status_code=400, detail="Username or email already taken")

  return {"status": "ok", "user": result.data[0]}