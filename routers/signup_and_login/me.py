from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from db.client import supabase
from services.auth import require_user
from services.game_data import migrate_game_data

router = APIRouter()

@router.get("/me")
def me(user=Depends(require_user)):
  result = supabase.table("User_Login_Data").select("*").eq("id", user.id).execute()
  if not result.data:
    raise HTTPException(status_code=404, detail="Account data not found")
  row = result.data[0]
  row["email"] = user.email
  row["game_data"] = migrate_game_data(row["game_data"])
  return {"user": row}

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

@router.get("/my_discord")
def my_discord(user=Depends(require_user)):
  result = supabase.table("User_Login_Data").select("premium_game_data").eq("id", user.id).single().execute()
  tier = int(result.data["premium_game_data"]["account_tier"].replace("account_tier_", ""))
  if tier < 5:
    raise HTTPException(status_code=403, detail="You must be Luxurious tier or higher for this")
  return {"discord": "thehandsomeguy67410"}
