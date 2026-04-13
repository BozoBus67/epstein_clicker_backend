from fastapi import APIRouter
from pydantic import BaseModel
from initializations_and_declarations.db_initialization import supabase
from initializations_and_declarations.game_data_declarations import INITIAL_GAME_DATA

router = APIRouter()

class SaveGameDataRequest(BaseModel):
  user_id: str
  game_data: dict

class ResetGameDataRequest(BaseModel):
  user_id: str

@router.post("/save_game_data")
def save_game_data(body: SaveGameDataRequest):
  result = supabase.table("User_Login_Data").update({
    "game_data": body.game_data,
  }).eq("id", body.user_id).execute()

  if not result.data:
    return {"status": "error"}

  return {"status": "ok"}

@router.post("/reset_game_data")
def reset_game_data(body: ResetGameDataRequest):
  result = supabase.table("User_Login_Data").update({
    "game_data": INITIAL_GAME_DATA,
  }).eq("id", body.user_id).execute()

  if not result.data:
    return {"status": "error"}

  return {"status": "ok", "game_data": INITIAL_GAME_DATA}