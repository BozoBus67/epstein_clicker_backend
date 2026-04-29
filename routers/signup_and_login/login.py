import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client, ClientOptions
from db.client import supabase
from services.game_data import migrate_game_data

router = APIRouter()

INVALID_CREDENTIALS = "Incorrect username/email or password"

class LoginRequest(BaseModel):
  username_or_email: str
  password: str

@router.post("/login")
def login(body: LoginRequest):
  email = body.username_or_email

  if "@" not in body.username_or_email:
    row = supabase.table("User_Login_Data").select("id").eq("username", body.username_or_email).execute()
    if not row.data:
      raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    auth_user = supabase.auth.admin.get_user_by_id(row.data[0]["id"])
    if not auth_user.user:
      raise HTTPException(status_code=500, detail="Account inconsistency — contact support")
    email = auth_user.user.email

  try:
    # Use a fresh client for sign_in so it doesn't pollute the global client's session state
    login_client = create_client(
      os.getenv("SUPABASE_URL"),
      os.getenv("SUPABASE_SECRET_KEY"),
      options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
    auth_result = login_client.auth.sign_in_with_password({"email": email, "password": body.password})
  except Exception as e:
    print(f"[login] sign_in_with_password error: {e}")
    msg = str(e)
    if "Email not confirmed" in msg:
      raise HTTPException(status_code=401, detail="Please confirm your email before logging in")
    if "Invalid login credentials" in msg:
      raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)
    if any(k in msg.lower() for k in ("rate limit", "too many", "limit exceeded", "over_email_send_rate_limit")):
      raise HTTPException(status_code=429, detail="Too many login attempts — try again later")
    raise HTTPException(status_code=500, detail="An unknown error occurred — please try again")

  user_id = auth_result.user.id
  jwt = auth_result.session.access_token

  result = supabase.table("User_Login_Data").select("*").eq("id", user_id).execute()
  if not result.data:
    raise HTTPException(status_code=404, detail="Account data not found — contact support")

  user = result.data[0]
  user["email"] = auth_result.user.email
  user["game_data"] = migrate_game_data(user["game_data"])

  return {"status": "ok", "jwt": jwt, "refresh_token": auth_result.session.refresh_token, "user": user}
