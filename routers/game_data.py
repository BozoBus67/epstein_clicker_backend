from fastapi import APIRouter
from pydantic import BaseModel
from initializations_and_declarations.db_initialization import supabase
import json

router = APIRouter()

class SaveGameDataRequest(BaseModel):
  user_id: str
  game_data: dict

@router.post("/save_game_data")
def save_game_data(body: SaveGameDataRequest):
  result = supabase.table("User_Login_Data").update({
    "game_data": body.game_data,
  }).eq("id", body.user_id).execute()

  if not result.data:
    return {"status": "error"}

  return {"status": "ok"}