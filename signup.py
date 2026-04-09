from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db_initialization import supabase
from scroll_declarations import MASTERY_SCROLLS

router = APIRouter()

class SignUpRequest(BaseModel):
  email: str
  username: str
  password: str

@router.post("/signup")
def signup(body: SignUpRequest):
  existing = supabase.table("User_Login_Data").select("id").or_(
    f"username.eq.{body.username},email.eq.{body.email}"
  ).execute()

  if existing.data:
    raise HTTPException(status_code=400, detail="Username or email already taken")

  initial_premium_game_data = {key: 0 for key in MASTERY_SCROLLS.keys()}

  supabase.table("User_Login_Data").insert({
    "email": body.email,
    "username": body.username,
    "password": body.password,
    "account_tier": "free",
    "premium_tokens": 0,
    "login_streak": 0,
    "premium_game_data": initial_premium_game_data,
  }).execute()

  return {"status": "ok"}