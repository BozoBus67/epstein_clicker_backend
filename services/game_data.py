from data.game_data import INITIAL_GAME_DATA

def migrate_game_data(saved: dict) -> dict:
  migrated = {**INITIAL_GAME_DATA, **saved}
  valid_building_keys = set(INITIAL_GAME_DATA["buildings"].keys())
  migrated["buildings"] = {
    key: saved.get("buildings", {}).get(key, 0)
    for key in valid_building_keys
  }
  migrated["version"] = INITIAL_GAME_DATA["version"]
  return migrated
