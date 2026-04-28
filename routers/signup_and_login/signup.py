from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.client import supabase
from data.game_data import INITIAL_GAME_DATA
from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA

router = APIRouter()

class SignUpRequest(BaseModel):
  email: str
  username: str
  password: str

@router.post("/signup")
def signup(body: SignUpRequest):
  try:
    auth_result = supabase.auth.admin.create_user({
      "email": body.email,
      "password": body.password,
      "email_confirm": False,
    })
  except Exception as e:
    print(f"[signup] create_user error: {e}")
    msg = str(e).lower()
    if "already registered" in msg or "already exists" in msg:
      raise HTTPException(status_code=409, detail="Email already registered")
    if "unable to validate" in msg or "invalid email" in msg:
      raise HTTPException(status_code=400, detail="Invalid email address")
    if "password" in msg:
      raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if "rate limit" in msg or "too many" in msg:
      raise HTTPException(status_code=429, detail="Too many signup attempts — try again later")
    raise HTTPException(status_code=500, detail=f"Auth service error: {e}")

  user_id = auth_result.user.id

  try:
    supabase.table("User_Login_Data").insert({
      "id": user_id,
      "username": body.username,
      "game_data": INITIAL_GAME_DATA,
      "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
    }).execute()
  except Exception as e:
    print(f"[signup] User_Login_Data insert error: {e}")
    supabase.auth.admin.delete_user(user_id)
    msg = str(e).lower()
    if "duplicate" in msg or "unique" in msg:
      raise HTTPException(status_code=409, detail="Username already taken")
    raise HTTPException(status_code=500, detail=f"Failed to save account data: {e}")

  try:
    auth_result = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
  except Exception as e:
    print(f"[signup] post-signup sign_in error: {e}")
    raise HTTPException(status_code=500, detail=f"Account created but auto-login failed: {e}")

  return {
    "status": "ok",
    "jwt": auth_result.session.access_token,
    "user": {
      "id": user_id,
      "username": body.username,
      "email": body.email,
      "game_data": INITIAL_GAME_DATA,
      "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
    },
  }
