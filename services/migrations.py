from db.client import supabase
from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA
from data.game_data import INITIAL_GAME_DATA

def ensure_user_data_complete(user_uuid: str) -> dict:
  user = supabase.table("User_Login_Data").select("game_data, premium_game_data").eq("id", user_uuid).single().execute().data
  gd = user["game_data"] or {}
  pgd = user["premium_game_data"] or {}

  added_pgd_keys = [k for k in INITIAL_PREMIUM_GAME_DATA if k not in pgd]
  for k in added_pgd_keys:
    pgd[k] = INITIAL_PREMIUM_GAME_DATA[k]

  added_gd_keys = [k for k in INITIAL_GAME_DATA if k not in gd and k != "buildings"]
  for k in added_gd_keys:
    gd[k] = INITIAL_GAME_DATA[k]

  added_building_keys = []
  removed_building_keys = []
  if not isinstance(gd.get("buildings"), dict):
    gd["buildings"] = {}
  for b in INITIAL_GAME_DATA["buildings"]:
    if b not in gd["buildings"]:
      added_building_keys.append(b)
      gd["buildings"][b] = INITIAL_GAME_DATA["buildings"][b]
  for b in list(gd["buildings"].keys()):
    if b not in INITIAL_GAME_DATA["buildings"]:
      removed_building_keys.append(b)
      del gd["buildings"][b]

  migrated = bool(added_pgd_keys or added_gd_keys or added_building_keys or removed_building_keys)
  if migrated:
    supabase.table("User_Login_Data").update({"game_data": gd, "premium_game_data": pgd}).eq("id", user_uuid).execute()

  return {
    "migrated": migrated,
    "added_premium_keys": added_pgd_keys,
    "added_game_keys": added_gd_keys,
    "added_building_keys": added_building_keys,
    "removed_building_keys": removed_building_keys,
  }
