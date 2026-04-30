import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from supabase import create_client
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SECRET_KEY'])

rows = supabase.table('User_Login_Data').select('id, premium_game_data').execute().data
fixed = 0
for row in rows:
    pgd = row['premium_game_data']
    if pgd.get('account_tier') == 'free':
        pgd['account_tier'] = 'account_tier_0'
        supabase.table('User_Login_Data').update({'premium_game_data': pgd}).eq('id', row['id']).execute()
        print(f"Fixed user {row['id']}")
        fixed += 1

print(f"Done — fixed {fixed} row(s)")
