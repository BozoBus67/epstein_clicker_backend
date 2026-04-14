from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from initializations_and_declarations.db_initialization import supabase
from utils import migrate_game_data

router = APIRouter()

class LoginRequest(BaseModel):
  username_or_email: str
  password: str

@router.post("/login")
def login(body: LoginRequest):
  # try treating input as email first, then fall back to username lookup
  try:
    auth_result = supabase.auth.sign_in_with_password({
      "email": body.username_or_email,
      "password": body.password,
    })
  except Exception:
    row = supabase.table("User_Login_Data").select("id").eq(
      "username", body.username_or_email
    ).execute()
    if not row.data:
      raise HTTPException(status_code=401, detail="Invalid credentials")

    auth_user = supabase.auth.admin.get_user_by_id(row.data[0]["id"])
    if not auth_user.user:
      raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
      auth_result = supabase.auth.sign_in_with_password({
        "email": auth_user.user.email,
        "password": body.password,
      })
    except Exception:
      raise HTTPException(status_code=401, detail="Invalid credentials")

  user_id = auth_result.user.id
  jwt = auth_result.session.access_token

  result = supabase.table("User_Login_Data").select(
    "id, username, game_data, premium_game_data"
  ).eq("id", user_id).execute()

  if not result.data:
    raise HTTPException(status_code=404, detail="User data not found")

  user = result.data[0]
  user["game_data"] = migrate_game_data(user["game_data"])

  return {
    "status": "ok",
    "jwt": jwt,
    "user": user,
  }