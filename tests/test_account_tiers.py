"""Tests for the buy_account_tier endpoint's validation logic.

Tier purchases are gated by three rules:
  1. Target tier must exist
  2. Target tier must be exactly the next tier (no skipping, no re-buying)
  3. User must have enough tokens

These are easy to get wrong if the constants drift, so they're worth pinning.
"""
import copy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from data.account_tiers import ACCOUNT_TIERS
from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA
from tests._fake_supabase import Fake_Supabase


@pytest.fixture
def patched_module(monkeypatch):
  from routers import account_tiers
  fake = Fake_Supabase()
  monkeypatch.setattr(account_tiers, "supabase", fake)
  return account_tiers, fake


def _user(uuid="user-1"):
  return SimpleNamespace(id=uuid)


def _row_with(tier_id, tokens):
  pgd = copy.deepcopy(INITIAL_PREMIUM_GAME_DATA)
  pgd["account_tier"] = tier_id
  pgd["tokens"] = tokens
  return {"premium_game_data": pgd}


def test_rejects_unknown_tier(patched_module):
  account_tiers, fake = patched_module
  fake.row = _row_with("account_tier_0", tokens=999_999)

  with pytest.raises(HTTPException) as exc:
    account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id="account_tier_999"), user=_user())

  assert exc.value.status_code == 400
  assert "Invalid tier" in exc.value.detail
  assert fake.last_update is None


def test_rejects_buying_current_tier(patched_module):
  account_tiers, fake = patched_module
  fake.row = _row_with("account_tier_3", tokens=999_999)

  with pytest.raises(HTTPException) as exc:
    account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id="account_tier_3"), user=_user())

  assert exc.value.status_code == 400
  assert "already have" in exc.value.detail.lower()
  assert fake.last_update is None


def test_rejects_buying_lower_tier(patched_module):
  account_tiers, fake = patched_module
  fake.row = _row_with("account_tier_5", tokens=999_999)

  with pytest.raises(HTTPException) as exc:
    account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id="account_tier_2"), user=_user())

  assert exc.value.status_code == 400
  assert "already have" in exc.value.detail.lower()
  assert fake.last_update is None


def test_rejects_skipping_a_tier(patched_module):
  account_tiers, fake = patched_module
  fake.row = _row_with("account_tier_1", tokens=999_999)

  with pytest.raises(HTTPException) as exc:
    account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id="account_tier_3"), user=_user())

  assert exc.value.status_code == 400
  assert "previous tier first" in exc.value.detail.lower()
  assert fake.last_update is None


def test_rejects_when_not_enough_tokens(patched_module):
  account_tiers, fake = patched_module
  next_tier = ACCOUNT_TIERS[2]
  fake.row = _row_with("account_tier_1", tokens=next_tier["token_price"] - 1)

  with pytest.raises(HTTPException) as exc:
    account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id=next_tier["id"]), user=_user())

  assert exc.value.status_code == 400
  assert "not enough tokens" in exc.value.detail.lower()
  assert fake.last_update is None


def test_successful_purchase_deducts_tokens_and_advances_tier(patched_module):
  account_tiers, fake = patched_module
  next_tier = ACCOUNT_TIERS[1]
  start_tokens = next_tier["token_price"] + 50
  fake.row = _row_with("account_tier_0", tokens=start_tokens)

  result = account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id=next_tier["id"]), user=_user())

  assert result["premium_game_data"]["account_tier"] == next_tier["id"]
  assert result["premium_game_data"]["tokens"] == start_tokens - next_tier["token_price"]
  assert fake.last_update["premium_game_data"]["account_tier"] == next_tier["id"]
  assert fake.last_update["premium_game_data"]["tokens"] == start_tokens - next_tier["token_price"]


def test_exact_token_amount_succeeds(patched_module):
  # Boundary: tokens == price should be allowed (the check is "<", not "<=")
  account_tiers, fake = patched_module
  next_tier = ACCOUNT_TIERS[1]
  fake.row = _row_with("account_tier_0", tokens=next_tier["token_price"])

  result = account_tiers.buy_account_tier(account_tiers.BuyTierRequest(tier_id=next_tier["id"]), user=_user())

  assert result["premium_game_data"]["tokens"] == 0
  assert result["premium_game_data"]["account_tier"] == next_tier["id"]
