from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db.client import supabase
from services.auth import require_user
from services.migrations import ensure_user_data_complete

router = APIRouter()

@router.get("/me")
def me(user=Depends(require_user)):
  migration_result = ensure_user_data_complete(user.id)
  result = supabase.table("User_Login_Data").select("*").eq("id", user.id).execute()
  if not result.data:
    raise HTTPException(status_code=404, detail="Account data not found")
  row = result.data[0]
  row["email"] = user.email
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
  if body.theme not in ("light", "dark"):
    raise HTTPException(status_code=400, detail="theme must be 'light' or 'dark'")
  pgd = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute().data["premium_game_data"]
  if body.theme == "dark" and pgd.get("mastery_scroll_12", 0) < 1:
    raise HTTPException(status_code=403, detail="You need at least 1 George Floyd mastery scroll to unlock dark mode.")
  pgd["theme"] = body.theme
  supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", user.id).execute()
  return {"theme": body.theme}

@router.get("/my_discord")
def my_discord(user=Depends(require_user)):
  result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
  tier = int(result.data["premium_game_data"]["account_tier"].replace("account_tier_", ""))
  if tier < 5:
    raise HTTPException(status_code=403, detail="You must be Luxurious tier or higher for this")
  return {"discord": "thehandsomeguy67410"}
