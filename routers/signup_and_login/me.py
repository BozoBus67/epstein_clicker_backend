from fastapi import APIRouter, Depends, HTTPException
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
