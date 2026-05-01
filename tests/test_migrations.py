"""Tests for ensure_user_data_complete — the function that reconciles a user's
stored game_data/premium_game_data with the canonical INITIAL_* shapes when
they log in. Important to keep correct because it runs on every login and silent
breakage means users get stuck with missing keys (which then crash feature
endpoints with 500s).
"""
import copy

import pytest

from data.game_data import INITIAL_GAME_DATA
from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA
from tests._fake_supabase import Fake_Supabase


def _full_initial_row():
  return {
    "game_data": copy.deepcopy(INITIAL_GAME_DATA),
    "premium_game_data": copy.deepcopy(INITIAL_PREMIUM_GAME_DATA),
  }


@pytest.fixture
def patched_module(monkeypatch):
  """Returns a (module, fake) pair where the module's `supabase` is replaced."""
  from services import migrations
  fake = Fake_Supabase()
  monkeypatch.setattr(migrations, "supabase", fake)
  return migrations, fake


def test_no_op_when_user_data_already_complete(patched_module):
  migrations, fake = patched_module
  fake.row = _full_initial_row()

  result = migrations.ensure_user_data_complete("user-1")

  assert result["migrated"] is False
  assert result["added_premium_keys"] == []
  assert result["added_game_keys"] == []
  assert result["added_building_keys"] == []
  assert result["removed_building_keys"] == []
  assert fake.last_update is None  # no write should occur


def test_adds_missing_premium_key(patched_module):
  migrations, fake = patched_module
  row = _full_initial_row()
  del row["premium_game_data"]["theme"]
  fake.row = row

  result = migrations.ensure_user_data_complete("user-1")

  assert result["migrated"] is True
  assert "theme" in result["added_premium_keys"]
  assert fake.last_update["premium_game_data"]["theme"] == INITIAL_PREMIUM_GAME_DATA["theme"]


def test_adds_missing_game_key(patched_module):
  migrations, fake = patched_module
  row = _full_initial_row()
  del row["game_data"]["cps"]
  fake.row = row

  result = migrations.ensure_user_data_complete("user-1")

  assert result["migrated"] is True
  assert "cps" in result["added_game_keys"]
  assert fake.last_update["game_data"]["cps"] == INITIAL_GAME_DATA["cps"]


def test_adds_missing_building(patched_module):
  migrations, fake = patched_module
  row = _full_initial_row()
  del row["game_data"]["buildings"]["building_5"]
  fake.row = row

  result = migrations.ensure_user_data_complete("user-1")

  assert result["migrated"] is True
  assert "building_5" in result["added_building_keys"]
  assert fake.last_update["game_data"]["buildings"]["building_5"] == 0


def test_removes_unknown_building(patched_module):
  migrations, fake = patched_module
  row = _full_initial_row()
  row["game_data"]["buildings"]["building_legacy"] = 42
  fake.row = row

  result = migrations.ensure_user_data_complete("user-1")

  assert result["migrated"] is True
  assert "building_legacy" in result["removed_building_keys"]
  assert "building_legacy" not in fake.last_update["game_data"]["buildings"]


def test_handles_null_jsonb_columns(patched_module):
  # If a row was inserted without these columns (or a manual SQL edit set them
  # to NULL), the migration should treat them as empty dicts and re-fill.
  migrations, fake = patched_module
  fake.row = {"game_data": None, "premium_game_data": None}

  result = migrations.ensure_user_data_complete("user-1")

  assert result["migrated"] is True
  assert set(result["added_premium_keys"]) == set(INITIAL_PREMIUM_GAME_DATA.keys())
  # game_data top-level keys minus "buildings" (buildings are tracked separately)
  expected_game_keys = {k for k in INITIAL_GAME_DATA if k != "buildings"}
  assert set(result["added_game_keys"]) == expected_game_keys


def test_idempotent_after_migration(patched_module):
  """Running it twice in a row: second call should be a no-op."""
  migrations, fake = patched_module
  row = _full_initial_row()
  del row["premium_game_data"]["theme"]
  fake.row = row

  first = migrations.ensure_user_data_complete("user-1")
  assert first["migrated"] is True

  # Apply what the migration wrote (simulating the post-write state)
  fake.row = {"game_data": fake.last_update["game_data"], "premium_game_data": fake.last_update["premium_game_data"]}
  fake.last_update = None

  second = migrations.ensure_user_data_complete("user-1")
  assert second["migrated"] is False
  assert fake.last_update is None
