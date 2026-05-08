"""Tests for the Stripe webhook — real-money flow, worth pinning.

Validation rules:
  - Invalid signature           → 400
  - Non-checkout.session events → 200 ignored, no DB write
  - Missing client_reference_id → 400, no DB write
  - Missing amount_total        → 400, no DB write
  - Zero / negative amount      → 400, no DB write
  - Happy path                  → tokens credited at amount_total // 100
  - Replayed event              → 200 already_processed, no DB write
"""
import asyncio
import copy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from data.premium_game_data import INITIAL_PREMIUM_GAME_DATA
from tests._fake_supabase import Fake_Supabase


def _request_with(body=b"{}", signature="sig"):
  """Minimal stand-in for Starlette's Request — enough surface for the endpoint."""
  return SimpleNamespace(
    body=lambda: _async_return(body),
    headers={"stripe-signature": signature},
  )


def _async_return(value):
  async def _coro():
    return value
  return _coro()


def _run(coro):
  return asyncio.run(coro)


def _user_row(tokens=0):
  pgd = copy.deepcopy(INITIAL_PREMIUM_GAME_DATA)
  pgd["tokens"] = tokens
  return {"premium_game_data": pgd}


@pytest.fixture
def patched(monkeypatch):
  from routers import payments
  fake = Fake_Supabase()
  monkeypatch.setattr(payments, "supabase", fake)
  return payments, fake


def test_invalid_signature_400(patched, monkeypatch):
  payments, _ = patched

  def boom(*_args, **_kwargs):
    raise ValueError("bad sig")
  monkeypatch.setattr(payments.stripe.Webhook, "construct_event", boom)

  with pytest.raises(HTTPException) as exc:
    _run(payments.stripe_webhook(_request_with()))

  assert exc.value.status_code == 400
  assert "Invalid signature" in exc.value.detail


def test_non_checkout_event_is_ignored(patched, monkeypatch):
  payments, fake = patched
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"type": "payment_intent.succeeded", "data": {"object": {}}},
  )

  result = _run(payments.stripe_webhook(_request_with()))

  assert result["status"] == "ignored"
  assert fake.last_update is None


def test_missing_client_reference_id_400(patched, monkeypatch):
  payments, fake = patched
  session = SimpleNamespace(client_reference_id=None, amount_total=999)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_test", "type": "checkout.session.completed", "data": {"object": session}},
  )

  with pytest.raises(HTTPException) as exc:
    _run(payments.stripe_webhook(_request_with()))

  assert exc.value.status_code == 400
  assert "client_reference_id" in exc.value.detail
  assert fake.last_update is None


def test_missing_amount_total_400(patched, monkeypatch):
  payments, fake = patched
  session = SimpleNamespace(client_reference_id="user-1", amount_total=None)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_test", "type": "checkout.session.completed", "data": {"object": session}},
  )

  with pytest.raises(HTTPException) as exc:
    _run(payments.stripe_webhook(_request_with()))

  assert exc.value.status_code == 400
  assert fake.last_update is None


def test_zero_amount_rejected(patched, monkeypatch):
  payments, fake = patched
  # 50 cents → 0 tokens after // 100 → rejected
  session = SimpleNamespace(client_reference_id="user-1", amount_total=50)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_test", "type": "checkout.session.completed", "data": {"object": session}},
  )
  fake.row = _user_row(tokens=10)

  with pytest.raises(HTTPException) as exc:
    _run(payments.stripe_webhook(_request_with()))

  assert exc.value.status_code == 400
  assert "Invalid token amount" in exc.value.detail
  assert fake.last_update is None


def test_happy_path_credits_tokens(patched, monkeypatch):
  payments, fake = patched
  # $5.00 → 500 cents → 5 tokens
  session = SimpleNamespace(client_reference_id="user-1", amount_total=500)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_test", "type": "checkout.session.completed", "data": {"object": session}},
  )
  fake.row = _user_row(tokens=10)

  result = _run(payments.stripe_webhook(_request_with()))

  assert result["status"] == "ok"
  assert fake.last_update["premium_game_data"]["tokens"] == 15  # 10 + 5


def test_credits_correct_token_count_at_round_dollar(patched, monkeypatch):
  payments, fake = patched
  # $25.00 → 2500 cents → 25 tokens
  session = SimpleNamespace(client_reference_id="user-1", amount_total=2500)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_test", "type": "checkout.session.completed", "data": {"object": session}},
  )
  fake.row = _user_row(tokens=0)

  result = _run(payments.stripe_webhook(_request_with()))

  assert result["status"] == "ok"
  assert fake.last_update["premium_game_data"]["tokens"] == 25


def test_replayed_event_returns_already_processed_no_credit(patched, monkeypatch):
  """Stripe retries can re-deliver the same event.id; we must not double-credit."""
  payments, fake = patched
  session = SimpleNamespace(client_reference_id="user-1", amount_total=500)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_already_seen", "type": "checkout.session.completed", "data": {"object": session}},
  )
  fake.row = _user_row(tokens=10)
  fake.processed_event_ids = ["evt_already_seen"]  # idempotency table already contains it

  result = _run(payments.stripe_webhook(_request_with()))

  assert result["status"] == "already_processed"
  assert result["event_id"] == "evt_already_seen"
  assert fake.last_update is None    # no credit applied
  assert fake.last_insert is None    # no new insert into the events table either


def test_happy_path_marks_event_processed(patched, monkeypatch):
  """After a successful credit the event id should be persisted so a retry skips."""
  payments, fake = patched
  session = SimpleNamespace(client_reference_id="user-1", amount_total=500)
  monkeypatch.setattr(
    payments.stripe.Webhook, "construct_event",
    lambda *a, **k: {"id": "evt_unique_999", "type": "checkout.session.completed", "data": {"object": session}},
  )
  fake.row = _user_row(tokens=0)

  _run(payments.stripe_webhook(_request_with()))

  assert fake.last_insert == {"event_id": "evt_unique_999"}
