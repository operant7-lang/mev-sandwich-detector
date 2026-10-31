import os, json, urllib.request, urllib.error

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_KEY"]

rows = [{
    "block": r["block"],
    "pool": r["pair"],
    "attacker": r["attacker"],
    "front_tx": r["front_tx"],
    "victim_txs": r["victim_txs"],
    "back_tx": r["back_tx"],
    "profit_pct_of_input": r["profit_pct_of_input"],
} for r in json.load(open("sandwiches.json"))]

if not rows:
    print("Nothing to save")
    raise SystemExit

headers = {
    "apikey": KEY,
    "Content-Type": "application/json",
    "Prefer": "resolution=ignore-duplicates,return=minimal",
    "User-Agent": "mev-detector/1.0",
}
if KEY.startswith("eyJ"):
    headers["Authorization"] = f"Bearer {KEY}"

req = urllib.request.Request(
    f"{URL}/rest/v1/sandwiches?on_conflict=front_tx,back_tx",
    data=json.dumps(rows).encode(), headers=headers, method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Saved {len(rows)} rows (status {r.status})")
except urllib.error.HTTPError as e:
    print("Error", e.code, e.read().decode())
