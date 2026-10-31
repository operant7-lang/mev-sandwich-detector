import os, sys, json, urllib.request

KEY = os.environ["ALCHEMY_KEY"]
URL = f"https://eth-mainnet.g.alchemy.com/v2/{KEY}"
SWAP_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
NUM_BLOCKS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
CHUNK = 5


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        URL, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "mev-detector/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.load(r)
    if "error" in j:
        raise RuntimeError(j["error"])
    return j["result"]


def get_logs(lo, hi):
    try:
        return rpc("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi),
                                    "topics": [SWAP_TOPIC]}])
    except Exception:
        if lo == hi:
            raise
        mid = (lo + hi) // 2
        return get_logs(lo, mid) + get_logs(mid + 1, hi)


def parse(log):
    d = log["data"][2:]
    if len(d) < 256:
        return None
    a0i, a1i, a0o, a1o = (int(d[i * 64:(i + 1) * 64], 16) for i in range(4))
    token_in = 0 if a0i > 0 else 1
    return {
        "pair": log["address"].lower(),
        "block": int(log["blockNumber"], 16),
        "idx": int(log["logIndex"], 16),
        "tx": log["transactionHash"],
        "to": "0x" + log["topics"][2][-40:].lower(),
        "dir": token_in,
        "amt_in": a0i if token_in == 0 else a1i,
        "amt_out": a1o if token_in == 0 else a0o,
    }


def find_sandwiches(swaps, pairs):
    swaps.sort(key=lambda s: s["idx"])
    found = []
    for i, front in enumerate(swaps):
        if front["amt_out"] == 0 or front["to"] in pairs:
            continue
        for k in range(i + 2, len(swaps)):
            back = swaps[k]
            if back["to"] != front["to"] or back["dir"] == front["dir"] or back["tx"] == front["tx"]:
                continue
            victims = [v for v in swaps[i + 1:k]
                       if v["dir"] == front["dir"] and v["to"] != front["to"]
                       and v["tx"] not in (front["tx"], back["tx"])]
            if not victims:
                continue
            if not (0.9 <= back["amt_in"] / front["amt_out"] <= 1.1):
                continue
            profit = back["amt_out"] - front["amt_in"]
            if profit <= 0:
                continue
            found.append({
                "block": front["block"],
                "pair": front["pair"],
                "attacker": front["to"],
                "front_tx": front["tx"],
                "victim_txs": [v["tx"] for v in victims],
                "back_tx": back["tx"],
                "profit_pct_of_input": round(100 * profit / front["amt_in"], 3),
            })
            break
    return found


def main():
    latest = int(rpc("eth_blockNumber", []), 16)
    start = latest - NUM_BLOCKS + 1
    groups, pairs, total = {}, set(), 0
    for lo in range(start, latest + 1, CHUNK):
        hi = min(lo + CHUNK - 1, latest)
        for lg in get_logs(lo, hi):
            s = parse(lg)
            if not s:
                continue
            pairs.add(s["pair"])
            groups.setdefault((s["block"], s["pair"]), []).append(s)
            total += 1

    results = []
    for swaps in groups.values():
        if len(swaps) >= 3:
            results += find_sandwiches(swaps, pairs)

    print(f"Scanned blocks {start}-{latest} | swaps: {total} | pools: {len(pairs)} | sandwiches found: {len(results)}")
    for r in results:
        print(f"\nBlock {r['block']}  pool https://etherscan.io/address/{r['pair']}")
        print(f"  attacker {r['attacker']}  profit ~ {r['profit_pct_of_input']}% of input (before gas)")
        print(f"  front : https://etherscan.io/tx/{r['front_tx']}")
        for v in r["victim_txs"]:
            print(f"  victim: https://etherscan.io/tx/{v}")
        print(f"  back  : https://etherscan.io/tx/{r['back_tx']}")

    with open("sandwiches.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
