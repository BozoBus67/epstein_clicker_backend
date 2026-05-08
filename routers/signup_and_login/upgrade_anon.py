from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError, AuthWeakPasswordError

from db.client import supabase
from routers.signup_and_login.signup import notify_discord_signup
from services.auth import require_user

router = APIRouter()

class UpgradeAnonRequest(BaseModel):
  email: str
  username: str
  password: str

# Promotes a Supabase anonymous user (signInAnonymously) into a permanent
# email+password user without creating a new auth row — same user.id, so the
# User_Login_Data row carries over and guest progress is preserved.
@router.post("/upgrade_anon")
def upgrade_anon(body: UpgradeAnonRequest, user=Depends(require_user)):
  if not getattr(user, "is_anonymous", False):
    raise HTTPException(status_code=400, detail="Account is already a permanent account")

  taken = supabase.table("User_Login_Data").select("id").eq("username", body.username).neq("id", user.id).execute()
  if taken.data:
    raise HTTPException(status_code=409, detail="Username already taken")

  try:
    supabase.auth.admin.update_user_by_id(user.id, {
      "email": body.email,
      "password": body.password,
      "email_confirm": True,
    })
  except AuthWeakPasswordError as e:
    raise HTTPException(status_code=400, detail=f"Weak password: {'; '.join(e.reasons)}")
  except AuthApiError as e:
    print(f"[upgrade_anon] update_user_by_id error: code={e.code} status={e.status} message={e.message}")
    if e.code in ("email_exists", "user_already_exists"):
      raise HTTPException(status_code=409, detail="Email already registered")
    if e.code == "email_address_invalid":
      raise HTTPException(status_code=400, detail="Invalid email address")
    raise HTTPException(status_code=e.status or 500, detail=e.message)

  supabase.table("User_Login_Data").update({"username": body.username}).eq("id", user.id).execute()

  notify_discord_signup(body.username, body.email)

  return {"status": "ok"}
