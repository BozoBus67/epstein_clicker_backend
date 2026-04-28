from fastapi import APIRouter, Depends
from pydantic import BaseModel
from db.client import supabase
from services.auth import require_user
from data.game_data import INITIAL_GAME_DATA

router = APIRouter()

class SaveGameDataRequest(BaseModel):
  game_data: dict

@router.post("/save_game_data")
def save_game_data(body: SaveGameDataRequest, user=Depends(require_user)):
  result = supabase.table("User_Login_Data").update({"game_data": body.game_data}).eq("id", user.id).execute()
  if not result.data:
    return {"status": "error"}
  return {"status": "ok"}

@router.post("/reset_game_data")
def reset_game_data(user=Depends(require_user)):
  result = supabase.table("User_Login_Data").update({"game_data": INITIAL_GAME_DATA}).eq("id", user.id).execute()
  if not result.data:
    return {"status": "error"}
  return {"status": "ok", "game_data": INITIAL_GAME_DATA}
