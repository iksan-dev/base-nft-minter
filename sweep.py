#!/usr/bin/env python3
"""
sweep.py — drain leftover ETH from every wallet back to a collector.

Each wallet sends (balance - gas_reserve). The gas reserve uses a 2x
buffer because the node validates (gas * maxFeePerGas + value) against the
balance; leaving zero headroom triggers "insufficient funds for gas".

Usage:
    python sweep.py wallets.txt --to 0xCOLLECTOR...
"""
import argparse
import json
import time

from common import get_w3, load_wallets, suggested_gas_price, CHAIN_ID, rpc_retry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wallet_file")
    ap.add_argument("--to", required=True, help="collector address")
    ap.add_argument("--out", default="sweep_results.json")
    args = ap.parse_args()

    w3 = get_w3()
    collector = w3.to_checksum_address(args.to)
    rows = load_wallets(args.wallet_file)

    gp = suggested_gas_price(w3)
    GAS = 21000
    gas_cost = GAS * gp * 2  # 2x safety buffer vs node validation

    results = []
    swept = 0
    total = 0
    for addr, priv in rows:
        a = w3.to_checksum_address(addr)
        bal = rpc_retry(lambda: w3.eth.get_balance(a), default=0)
        send_val = bal - gas_cost
        if send_val <= 0:
            results.append({"addr": addr, "bal": bal, "sent": 0, "status": "dust_skip"})
            print(f"{addr} bal {bal} -> SKIP (below gas)")
            time.sleep(0.3)
            continue
        h = None
        err = None
        try:
            nonce = w3.eth.get_transaction_count(a)
            tx = {
                "to": collector, "value": send_val, "gas": GAS, "maxFeePerGas": gp,
                "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"), "nonce": nonce,
                "chainId": CHAIN_ID, "type": 2,
            }
            signed = w3.eth.account.sign_transaction(tx, priv)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
        except Exception as e:
            err = str(e)[:120]
        if h:
            results.append({"addr": addr, "bal": bal, "sent": send_val, "tx": h.hex(), "status": "sent"})
            swept += 1
            total += send_val
            print(f"{addr} sweep {w3.from_wei(send_val,'ether')} ETH -> {h.hex()}")
        else:
            results.append({"addr": addr, "bal": bal, "sent": 0, "status": "fail", "err": err})
            print(f"{addr} -> FAIL: {err}")
        time.sleep(0.4)

    json.dump(results, open(args.out, "w"), indent=2)
    print(f"\nSWEPT: {swept}/{len(rows)} | total to collector: {w3.from_wei(total,'ether')} ETH")


if __name__ == "__main__":
    main()
