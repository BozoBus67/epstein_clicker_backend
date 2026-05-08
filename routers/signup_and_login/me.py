from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from data.game_data import INITIAL_GAME_DATA
from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA
from db.client import supabase
from services.auth import require_user
from services.migrations import ensure_user_data_complete

router = APIRouter()

# Anonymous users (Supabase signInAnonymously) hit /me with a valid JWT but
# no User_Login_Data row yet — guests are real auth users created on first
# page load, but the game-data row is created here on first contact. The
# `guest_<prefix>` username is unique because it's keyed off the user uuid.
def ensure_user_login_data_row(user) -> bool:
  existing = supabase.table("User_Login_Data").select("id").eq("id", user.id).execute()
  if existing.data:
    return False
  guest_username = f"guest_{user.id[:8]}"
  supabase.table("User_Login_Data").insert({
    "id": user.id,
    "username": guest_username,
    "game_data": INITIAL_GAME_DATA,
    "premium_game_data": INITIAL_PREMIUM_GAME_DATA,
  }).execute()
  return True

@router.get("/me")
def me(user=Depends(require_user)):
  ensure_user_login_data_row(user)
  migration_result = ensure_user_data_complete(user.id)
  result = supabase.table("User_Login_Data").select("*").eq("id", user.id).execute()
  if not result.data:
    raise HTTPException(status_code=404, detail="Account data not found")
  row = result.data[0]
  row["email"] = user.email
  row["is_anonymous"] = bool(getattr(user, "is_anonymous", False))
  return {
    "user": row,
    "migration_info": migration_result if migration_result["migrated"] else None,
  }

class UpdateUsernameRequest(BaseModel):
  username: str

@router.patch("/me/username")
def update_username(body: UpdateUsernameRequest, user=Depends(require_user)):
  username = body.username.strip()
  if not username:
    raise HTTPException(status_code=400, detail="Username cannot be empty")
  taken = supabase.table("User_Login_Data").select("id").eq("username", username).neq("id", user.id).execute()
  if taken.data:
    raise HTTPException(status_code=409, detail="Username already taken")
  supabase.table("User_Login_Data").update({"username": username}).eq("id", user.id).execute()
  return {"username": username}

class UpdateThemeRequest(BaseModel):
  theme: str

@router.patch("/me/theme")
def update_theme(body: UpdateThemeRequest, user=Depends(require_user)):
  if body.theme not in ("default", "light", "dark"):
    raise HTTPException(status_code=400, detail="theme must be 'default', 'light', or 'dark'")
  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  if body.theme == "dark" and pgd["george_floyd"] < 1:
    raise HTTPException(status_code=403, detail="You need at least 1 George Floyd mastery scroll to unlock dark mode.")
  if body.theme == "light" and pgd["state_trooper_cop"] < 1:
    raise HTTPException(status_code=403, detail="You need at least 1 State Trooper mastery scroll to unlock light mode.")
  pgd["theme"] = body.theme
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"theme": body.theme}

class UpdateKirkModeRequest(BaseModel):
  enabled: bool

@router.patch("/me/kirk_mode")
def update_kirk_mode(body: UpdateKirkModeRequest, user=Depends(require_user)):
  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  # Toggling ON requires owning the Charlie Kirk scroll. Toggling OFF is
  # always allowed — even if the scroll was somehow lost, users can still
  # disable a mode they no longer own (avoids stuck-on UX).
  if body.enabled and pgd["charlie_kirk"] < 1:
    raise HTTPException(status_code=403, detail="You need at least 1 Charlie Kirk mastery scroll to unlock Kirk Mode.")
  pgd["kirk_mode"] = body.enabled
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"kirk_mode": body.enabled}

@router.get("/my_discord")
def my_discord(user=Depends(require_user)):
  result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
  tier = int(result.data["premium_game_data"]["account_tier"].replace("account_tier_", ""))
  if tier < 5:
    raise HTTPException(status_code=403, detail="You must be Luxurious tier or higher for this")
  return {"discord": "thehandsomeguy67410"}
