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
  # create the auth user first — supabase auth owns email + password
  try:
    auth_result = supabase.auth.admin.create_user({
      "email": body.email,
      "password": body.password,
      "email_confirm": True,
    })
  except Exception:
    raise HTTPException(status_code=409, detail="Email already registered")

  user_id = auth_result.user.id

  # insert our own row linked by the same uuid
  # if this fails, delete the auth user to avoid orphaned auth rows
  try:
    result = supabase.table("User_Login_Data").insert({
      "id": user_id,
      "username": body.username,
      "game_data": INITIAL_GAME_DATA,
      "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
    }).execute()
  except Exception:
    supabase.auth.admin.delete_user(user_id)
    raise HTTPException(status_code=409, detail="Username already taken")

  supabase.auth.admin.generate_link({
    "type": "signup",
    "email": body.email,
  })

  return {"status": "ok"}