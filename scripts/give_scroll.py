"""Grant a mastery scroll to a user. Replaces the per-scroll scripts
(give_kirk_scroll.py, give_floyd_scroll.py, etc.) with one parameterized
entry point.

Usage:
  python scripts/give_scroll.py <slug> [amount] [--username NAME]

Examples:
  python scripts/give_scroll.py blurry_epstein           # +1 Shadow Clone Jutsu
  python scripts/give_scroll.py diddy 5                  # +5 Diddy
  python scripts/give_scroll.py charlie_kirk --username user2

Slug validation hits MASTERY_SCROLLS, so a typo gets a clear error rather than
silently writing a garbage key into pgd."""

import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from data.scrolls import MASTERY_SCROLLS
from db.client import supabase

parser = argparse.ArgumentParser(description="Grant a mastery scroll.")
parser.add_argument("slug", help="Scroll slug (e.g. charlie_kirk, blurry_epstein)")
parser.add_argument("amount", nargs="?", type=int, default=1, help="How many to grant (default 1)")
parser.add_argument("--username", default="user1", help="Target username (default user1)")
args = parser.parse_args()

if args.slug not in MASTERY_SCROLLS:
  valid = ", ".join(sorted(MASTERY_SCROLLS.keys()))
  sys.exit(f"Unknown scroll slug '{args.slug}'. Valid slugs:\n  {valid}")

row = supabase.table("User_Login_Data").select("id, premium_game_data").eq("username", args.username).single().execute().data
pgd = row["premium_game_data"]
pgd[args.slug] = pgd.get(args.slug, 0) + args.amount
supabase.table("User_Login_Data").update({"premium_game_data": pgd}).eq("id", row["id"]).execute()
print(f"Done — {args.username} now has {pgd[args.slug]}× {args.slug}")
